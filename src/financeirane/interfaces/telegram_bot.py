import logging
import re
import unicodedata
from dataclasses import replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from financeirane.domain.exceptions import (
    EntradaInvalidaError,
    IAErroInesperado,
    IAIndisponivelError,
    IAQuotaExcedidaError,
    InterpretacaoIAError,
)
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
DATA_NUMERICA = re.compile(
    r"(?<![\d/])(?P<dia>\d{1,2})/(?P<mes>\d{1,2})"
    r"(?:/(?P<ano>\d+))?(?![\d/])"
)


def data_atual_bahia():
    return datetime.now(ZoneInfo("America/Bahia")).date()


def formatar_data(data):
    return data.strftime("%d/%m/%Y")


def resolver_data_numerica(texto_normalizado):
    for correspondencia in DATA_NUMERICA.finditer(texto_normalizado):
        antes = texto_normalizado[: correspondencia.start()]
        depois = texto_normalizado[correspondencia.end() :]
        if re.search(r"(?:parcela(?:s)?|r\$)\s*$", antes) or re.match(
            r"\s+(?:parcelas?\b|(?:do|da)\s+(?:valor|total|preco)\b)", depois
        ):
            continue

        ano_textual = correspondencia.group("ano")
        dia = int(correspondencia.group("dia"))
        mes = int(correspondencia.group("mes"))
        contexto_data = re.search(r"\b(?:no\s+dia|dia|em)\s*$", antes)
        if (
            not contexto_data
            and ano_textual is None
            and not (1 <= dia <= 31 and 1 <= mes <= 12)
        ):
            continue

        if ano_textual is not None and len(ano_textual) != 4:
            raise EntradaInvalidaError("Data inválida. Use DD/MM ou DD/MM/AAAA.")
        ano = int(ano_textual) if ano_textual else data_atual_bahia().year
        try:
            data_resolvida = date(ano, mes, dia)
        except ValueError as exc:
            raise EntradaInvalidaError(
                "Data inválida. Use DD/MM ou DD/MM/AAAA."
            ) from exc
        return formatar_data(data_resolvida)

    return None


def contem_data_textual_explicita(texto):
    texto_normalizado = normalizar_texto_consulta(texto)

    meses = "|".join(MESES_NOMEADOS)
    padrao_data_textual = (
        rf"\b(?:dia\s+)?\d{{1,2}}\s+de\s+(?:{meses})(?:\s+de\s+\d{{4}})?\b"
    )
    return re.search(padrao_data_textual, texto_normalizado) is not None


def resolver_data_registro(texto):
    texto_normalizado = normalizar_texto_consulta(texto)
    data_numerica = resolver_data_numerica(texto_normalizado)
    if data_numerica is not None:
        return data_numerica

    if contem_data_textual_explicita(texto):
        return None

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


def informar_data_numerica_invalida(bot, chat_id, texto):
    try:
        resolver_data_numerica(normalizar_texto_consulta(texto))
    except EntradaInvalidaError:
        bot.send_message(chat_id, "Data inválida. Use DD/MM ou DD/MM/AAAA.")
        logger.warning(
            "Data numérica inválida em registro. operacao=resolver_data_registro categoria=invalid_date"
        )
        return True
    return False


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

        except IAQuotaExcedidaError:
            bot.send_message(
                chat_id,
                "A FinanceirAne atingiu temporariamente o limite de uso da IA. Tente novamente mais tarde.",
            )
        except IAIndisponivelError:
            bot.send_message(
                chat_id,
                "A IA está temporariamente indisponível. Tente novamente em alguns instantes.",
            )
        except IAErroInesperado:
            bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
        except EntradaInvalidaError as exc:
            if informar_data_numerica_invalida(bot, chat_id, texto):
                return
            bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
            logger.error(
                "Entrada inválida. operacao=processar_mensagem erro=%s duracao_ms=%s",
                exc.__class__.__name__,
                duracao_ms(inicio),
            )
        except InterpretacaoIAError as exc:
            bot.send_message(chat_id, "Ops, ocorreu um erro ao processar o seu pedido.")
            logger.error(
                "Resposta da IA inválida. operacao=processar_mensagem categoria=unexpected_error erro=%s duracao_ms=%s",
                exc.__class__.__name__,
                duracao_ms(inicio),
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

    from financeirane.config import APP_ENV, TELEGRAM_TOKEN
    from financeirane.sheets_service import conectar_planilha

    planilha = conectar_planilha()
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    registrar_handlers(bot, planilha)
    logger.info(
        "A FinanceirAne está online. operacao=inicializar_bot ambiente=%s",
        APP_ENV,
    )
    return bot
