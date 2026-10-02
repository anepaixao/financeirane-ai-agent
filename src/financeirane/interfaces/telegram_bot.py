import logging
import re
import unicodedata
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from financeirane.logging_config import duracao_ms, iniciar_medicao, mascarar_id

logger = logging.getLogger("main")


def normalizar_texto_consulta(texto):
    texto_normalizado = unicodedata.normalize("NFKD", texto or "")
    texto_sem_acentos = "".join(
        caractere
        for caractere in texto_normalizado
        if not unicodedata.combining(caractere)
    )
    return texto_sem_acentos.lower()


def consulta_mes_atual(texto):
    texto_normalizado = normalizar_texto_consulta(texto)
    expressoes_relativas = (
        "esse mes",
        "este mes",
        "desse mes",
        "neste mes",
        "deste mes",
    )
    return any(expressao in texto_normalizado for expressao in expressoes_relativas)


def resolver_periodo_consulta(texto, dados):
    if consulta_mes_atual(texto):
        hoje = datetime.now(ZoneInfo("America/Bahia"))
        return f"{hoje.month:02d}", str(hoje.year)

    return dados.get("mes"), dados.get("ano")


MESES_NOMEADOS = (
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def data_atual_bahia():
    return datetime.now(ZoneInfo("America/Bahia")).date()


def formatar_data(data):
    return data.strftime("%d/%m/%Y")


def contem_data_explicita(texto):
    texto_normalizado = normalizar_texto_consulta(texto)
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", texto_normalizado):
        return True

    meses = "|".join(MESES_NOMEADOS)
    padrao_data_textual = (
        rf"\b(?:dia\s+)?\d{{1,2}}\s+de\s+(?:{meses})(?:\s+de\s+\d{{4}})?\b"
    )
    return re.search(padrao_data_textual, texto_normalizado) is not None


def resolver_data_registro(texto):
    if contem_data_explicita(texto):
        return None

    texto_normalizado = normalizar_texto_consulta(texto)
    hoje = data_atual_bahia()

    if re.search(r"\banteontem\b", texto_normalizado):
        return formatar_data(hoje - timedelta(days=2))

    if re.search(r"\bontem\b", texto_normalizado):
        return formatar_data(hoje - timedelta(days=1))

    return formatar_data(hoje)


def aplicar_data_deterministica_registro(texto, registro):
    data_resolvida = resolver_data_registro(texto)
    if data_resolvida is None:
        return registro

    return replace(registro, data=data_resolvida)


def registrar_handlers(bot, planilha):
    from financeirane.ai_service import interpretar_mensagem
    from financeirane.config import AUTHORIZED_CHAT_IDS, MAX_MESSAGE_LENGTH
    from financeirane.domain.models import RegistroFinanceiro
    from financeirane.sheets_service import consultar_gastos_mes, registrar_movimentacao

    @bot.message_handler(func=lambda message: True)
    def responder_mensagem(message):
        texto = message.text
        chat_id = message.chat.id
        user_id = getattr(getattr(message, "from_user", None), "id", None)

        if user_id not in AUTHORIZED_CHAT_IDS:
            logger.warning(
                "Mensagem ignorada de usuário não autorizado. operacao=autorizar_usuario user_ref=%s",
                mascarar_id(user_id),
            )
            return

        if not texto:
            bot.send_message(chat_id, "Envie uma mensagem de texto para eu processar.")
            return

        if texto in ("/id", "/meu_id"):
            bot.send_message(
                chat_id,
                f"O seu user ID é: `{user_id}`\nO ID deste chat é: `{chat_id}`",
                parse_mode="Markdown",
            )
            return

        if len(texto) > MAX_MESSAGE_LENGTH:
            bot.send_message(
                chat_id, "Mensagem muito longa. Envie um pedido mais curto."
            )
            return

        bot.send_message(chat_id, "⏳ A processar...")

        inicio = iniciar_medicao()

        try:
            logger.info(
                "Mensagem autorizada recebida. operacao=processar_mensagem tamanho=%s user_ref=%s",
                len(texto),
                mascarar_id(user_id),
            )

            dados = interpretar_mensagem(texto)

            intencao = (
                "registrar"
                if isinstance(dados, RegistroFinanceiro)
                else dados.get("intencao")
            )
            logger.info(
                "Intenção detectada pela IA. operacao=interpretar_mensagem intencao=%s",
                intencao,
            )

            if intencao == "registrar":
                dados = aplicar_data_deterministica_registro(texto, dados)
                resposta = registrar_movimentacao(planilha, dados)
                bot.send_message(chat_id, resposta)
                logger.info(
                    "Fluxo de registro concluído com sucesso. operacao=registrar_movimentacao duracao_ms=%s",
                    duracao_ms(inicio),
                )
                return

            if intencao == "consultar":
                mes_consulta, ano_consulta = resolver_periodo_consulta(texto, dados)
                resposta = consultar_gastos_mes(planilha, mes_consulta, ano_consulta)
                bot.send_message(chat_id, resposta, parse_mode="Markdown")
                logger.info(
                    "Fluxo de consulta concluído com sucesso. operacao=consultar_movimentacoes duracao_ms=%s",
                    duracao_ms(inicio),
                )
                return

            bot.send_message(
                chat_id,
                "Não consegui entender se você quer registrar ou consultar uma informação.",
            )

        except Exception as exc:
            bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
            logger.exception(
                "Erro ao processar mensagem autorizada. operacao=processar_mensagem erro=%s duracao_ms=%s",
                exc.__class__.__name__,
                duracao_ms(inicio),
            )


def criar_bot():
    import telebot

    from financeirane.config import TELEGRAM_TOKEN
    from financeirane.sheets_service import conectar_planilha

    planilha = conectar_planilha()
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    registrar_handlers(bot, planilha)
    logger.info("A FinanceirAne está online. operacao=inicializar_bot")
    return bot
