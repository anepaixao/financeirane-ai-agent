import importlib
import logging
import runpy
import sys
from dataclasses import dataclass
from datetime import datetime as DateTime
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import financeirane.main as package_main
import main
from financeirane.interfaces import telegram_bot

AUTHORIZED_USER_ID = 123456789
CHAT_ID = 987654321
MAX_MESSAGE_LENGTH = 100


class FakeBot:
    def __init__(self):
        self.handler = None
        self.send_message = Mock()

    def message_handler(self, **_kwargs):
        def decorator(func):
            self.handler = func
            return func

        return decorator


@dataclass
class RegistroFinanceiroFake:
    data: str = "15/09/2026"
    tipo: str = "gasto"
    valor_total: float = 20.0
    descricao: str = "Mercado"
    parcelas: int = 1
    categoria: str = "Outros"


def criar_modulo(nome, **atributos):
    modulo = ModuleType(nome)
    for chave, valor in atributos.items():
        setattr(modulo, chave, valor)
    return modulo


def criar_mensagem(texto, user_id=AUTHORIZED_USER_ID):
    mensagem = SimpleNamespace(text=texto, chat=SimpleNamespace(id=CHAT_ID))
    if user_id is not None:
        mensagem.from_user = SimpleNamespace(id=user_id)
    return mensagem


def preparar_handler():
    planilha = object()
    dependencias = {
        "interpretar_mensagem": Mock(name="interpretar_mensagem"),
        "registrar_movimentacao": Mock(name="registrar_movimentacao"),
        "consultar_gastos_mes": Mock(name="consultar_gastos_mes"),
        "planilha": planilha,
    }

    modulos = {
        "financeirane.ai_service": criar_modulo(
            "financeirane.ai_service",
            interpretar_mensagem=dependencias["interpretar_mensagem"],
        ),
        "financeirane.config": criar_modulo(
            "financeirane.config",
            AUTHORIZED_CHAT_IDS={AUTHORIZED_USER_ID},
            MAX_MESSAGE_LENGTH=MAX_MESSAGE_LENGTH,
        ),
        "financeirane.domain.models": criar_modulo(
            "financeirane.domain.models", RegistroFinanceiro=RegistroFinanceiroFake
        ),
        "financeirane.sheets_service": criar_modulo(
            "financeirane.sheets_service",
            consultar_gastos_mes=dependencias["consultar_gastos_mes"],
            registrar_movimentacao=dependencias["registrar_movimentacao"],
        ),
    }

    bot = FakeBot()

    with patch.dict(sys.modules, modulos):
        telegram_bot.registrar_handlers(bot, planilha)

    return bot, dependencias


def assert_servicos_nao_foram_chamados(dependencias):
    dependencias["interpretar_mensagem"].assert_not_called()
    dependencias["registrar_movimentacao"].assert_not_called()
    dependencias["consultar_gastos_mes"].assert_not_called()


def test_usuario_nao_autorizado_e_ignorado():
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem("gastei 10", user_id=999))

    bot.send_message.assert_not_called()
    assert_servicos_nao_foram_chamados(dependencias)


def test_usuario_nao_autorizado_nao_expoe_id_completo_no_log(caplog):
    bot, dependencias = preparar_handler()
    user_id = 1234567890

    with caplog.at_level(logging.WARNING, logger="main"):
        bot.handler(criar_mensagem("gastei 10", user_id=user_id))

    assert str(user_id) not in caplog.text
    assert "7890" in caplog.text
    bot.send_message.assert_not_called()
    assert_servicos_nao_foram_chamados(dependencias)


def test_mensagem_sem_from_user_e_ignorada():
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem("gastei 10", user_id=None))

    bot.send_message.assert_not_called()
    assert_servicos_nao_foram_chamados(dependencias)


def test_mensagem_vazia_de_usuario_autorizado_envia_aviso():
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem(""))

    bot.send_message.assert_called_once_with(
        CHAT_ID, "Envie uma mensagem de texto para eu processar."
    )
    assert_servicos_nao_foram_chamados(dependencias)


@pytest.mark.parametrize("comando", ["/id", "/meu_id"])
def test_comando_de_id_responde_ids_do_usuario_e_chat(comando):
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem(comando))

    bot.send_message.assert_called_once_with(
        CHAT_ID,
        f"O seu user ID é: `{AUTHORIZED_USER_ID}`\nO ID deste chat é: `{CHAT_ID}`",
        parse_mode="Markdown",
    )
    assert_servicos_nao_foram_chamados(dependencias)


def test_mensagem_acima_do_limite_envia_aviso():
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem("x" * (MAX_MESSAGE_LENGTH + 1)))

    bot.send_message.assert_called_once_with(
        CHAT_ID, "Mensagem muito longa. Envie um pedido mais curto."
    )
    assert_servicos_nao_foram_chamados(dependencias)


def test_logs_do_handler_nao_contem_mensagem_financeira_nem_valor(caplog):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = RegistroFinanceiroFake()
    dependencias["registrar_movimentacao"].return_value = "Registrado"
    texto_mensagem = "gastei 987654321 no mercado secreto"

    with caplog.at_level(logging.INFO):
        bot.handler(criar_mensagem(texto_mensagem))

    assert texto_mensagem not in caplog.text
    assert "987654321" not in caplog.text
    dependencias["registrar_movimentacao"].assert_called_once()
    dependencias["consultar_gastos_mes"].assert_not_called()


def test_usuario_autorizado_com_registro_chama_ia_e_planilha():
    bot, dependencias = preparar_handler()
    registro = RegistroFinanceiroFake()
    dependencias["interpretar_mensagem"].return_value = registro
    dependencias["registrar_movimentacao"].return_value = "Registrado com sucesso"

    bot.handler(criar_mensagem("gastei 20 no mercado em 15/09/2026"))

    dependencias["interpretar_mensagem"].assert_called_once_with(
        "gastei 20 no mercado em 15/09/2026"
    )
    dependencias["registrar_movimentacao"].assert_called_once_with(
        dependencias["planilha"], registro
    )
    dependencias["consultar_gastos_mes"].assert_not_called()
    assert bot.send_message.call_args_list[-1].args == (
        CHAT_ID,
        "Registrado com sucesso",
    )


class DataRegistroFixa:
    @staticmethod
    def now(_timezone):
        return DateTime(2026, 10, 2)


class DataRegistroViradaMes:
    @staticmethod
    def now(_timezone):
        return DateTime(2026, 10, 1)


class DataRegistroViradaAno:
    @staticmethod
    def now(_timezone):
        return DateTime(2027, 1, 1)


@pytest.mark.parametrize(
    ("texto", "data_esperada"),
    [
        ("Comprei um açaí de 15 reais", "02/10/2026"),
        ("Comprei um café hoje por 8 reais", "02/10/2026"),
        ("Gastei 30 reais ontem no mercado", "01/10/2026"),
        ("Comprei um lanche anteontem por 20 reais", "30/09/2026"),
    ],
)
def test_registro_resolve_datas_relativas_e_ausentes(monkeypatch, texto, data_esperada):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = RegistroFinanceiroFake(
        data="01/01/1999"
    )
    dependencias["registrar_movimentacao"].return_value = "Registrado"
    monkeypatch.setattr(telegram_bot, "datetime", DataRegistroFixa)

    bot.handler(criar_mensagem(texto))

    registro = dependencias["registrar_movimentacao"].call_args.args[1]
    assert registro.data == data_esperada
    assert registro.tipo == "gasto"
    assert registro.valor_total == 20.0
    assert registro.descricao == "Mercado"
    assert registro.parcelas == 1
    assert registro.categoria == "Outros"


def test_registro_ontem_considera_virada_de_mes(monkeypatch):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = RegistroFinanceiroFake(
        data="01/01/1999"
    )
    dependencias["registrar_movimentacao"].return_value = "Registrado"
    monkeypatch.setattr(telegram_bot, "datetime", DataRegistroViradaMes)

    bot.handler(criar_mensagem("Gastei 30 reais ontem no mercado"))

    registro = dependencias["registrar_movimentacao"].call_args.args[1]
    assert registro.data == "30/09/2026"


def test_registro_ontem_considera_virada_de_ano(monkeypatch):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = RegistroFinanceiroFake(
        data="01/01/1999"
    )
    dependencias["registrar_movimentacao"].return_value = "Registrado"
    monkeypatch.setattr(telegram_bot, "datetime", DataRegistroViradaAno)

    bot.handler(criar_mensagem("Gastei 30 reais ontem no mercado"))

    registro = dependencias["registrar_movimentacao"].call_args.args[1]
    assert registro.data == "31/12/2026"


@pytest.mark.parametrize(
    "texto",
    [
        "Comprei um tênis em 15/09/2026 por 200 reais",
        "Comprei um tênis dia 15 de setembro por 200 reais",
        "Comprei um tênis 15 de setembro de 2026 por 200 reais",
    ],
)
def test_registro_preserva_data_explicita_interpretada_pela_ia(monkeypatch, texto):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = RegistroFinanceiroFake(
        data="15/09/2026"
    )
    dependencias["registrar_movimentacao"].return_value = "Registrado"
    monkeypatch.setattr(telegram_bot, "datetime", DataRegistroFixa)

    bot.handler(criar_mensagem(texto))

    registro = dependencias["registrar_movimentacao"].call_args.args[1]
    assert registro.data == "15/09/2026"


def test_usuario_autorizado_com_consulta_chama_consultar_gastos_mes():
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = {
        "intencao": "consultar",
        "mes": "09",
        "ano": "2026",
    }
    dependencias["consultar_gastos_mes"].return_value = "Resumo do mês"

    bot.handler(criar_mensagem("quanto gastei em setembro de 2026?"))

    dependencias["interpretar_mensagem"].assert_called_once_with(
        "quanto gastei em setembro de 2026?"
    )
    dependencias["consultar_gastos_mes"].assert_called_once_with(
        dependencias["planilha"], "09", "2026"
    )
    dependencias["registrar_movimentacao"].assert_not_called()
    bot.send_message.assert_any_call(CHAT_ID, "Resumo do mês", parse_mode="Markdown")


class DataFixa:
    @staticmethod
    def now(_timezone):
        return SimpleNamespace(month=9, year=2026)


@pytest.mark.parametrize(
    "texto",
    [
        "quanto gastei esse mês?",
        "quanto gastei este mês?",
        "meus gastos desse mês",
        "quanto gastei neste mês?",
        "meus gastos deste mês",
    ],
)
def test_consulta_relativa_mes_atual_usa_periodo_da_aplicacao(monkeypatch, texto):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = {
        "intencao": "consultar",
        "mes": "01",
        "ano": "1999",
    }
    dependencias["consultar_gastos_mes"].return_value = "Resumo do mês"
    monkeypatch.setattr(telegram_bot, "datetime", DataFixa)

    bot.handler(criar_mensagem(texto))

    dependencias["interpretar_mensagem"].assert_called_once_with(texto)
    dependencias["consultar_gastos_mes"].assert_called_once_with(
        dependencias["planilha"], "09", "2026"
    )
    dependencias["registrar_movimentacao"].assert_not_called()


def test_consulta_explicita_preserva_periodo_inferido_pela_ia(monkeypatch):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = {
        "intencao": "consultar",
        "mes": "06",
        "ano": "2026",
    }
    dependencias["consultar_gastos_mes"].return_value = "Resumo de junho"
    monkeypatch.setattr(telegram_bot, "datetime", DataFixa)

    bot.handler(criar_mensagem("quanto gastei em junho de 2026?"))

    dependencias["consultar_gastos_mes"].assert_called_once_with(
        dependencias["planilha"], "06", "2026"
    )
    dependencias["registrar_movimentacao"].assert_not_called()


def test_intencao_inesperada_envia_mensagem_segura():
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = {"intencao": "desconhecida"}

    bot.handler(criar_mensagem("mensagem ambigua"))

    dependencias["interpretar_mensagem"].assert_called_once_with("mensagem ambigua")
    dependencias["registrar_movimentacao"].assert_not_called()
    dependencias["consultar_gastos_mes"].assert_not_called()
    assert bot.send_message.call_args_list[-1].args == (
        CHAT_ID,
        "Não consegui entender se você quer registrar ou consultar uma informação.",
    )


def test_falha_da_ia_envia_fallback_e_nao_chama_planilha(caplog):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].side_effect = RuntimeError("falha Gemini")
    texto_mensagem = "paguei 987654321 no mercado secreto"

    with caplog.at_level(logging.ERROR, logger="main"):
        bot.handler(criar_mensagem(texto_mensagem))

    dependencias["interpretar_mensagem"].assert_called_once_with(texto_mensagem)
    dependencias["registrar_movimentacao"].assert_not_called()
    dependencias["consultar_gastos_mes"].assert_not_called()
    assert bot.send_message.call_args_list[-1].args == (
        CHAT_ID,
        "Ops, ocorreu um erro ao processar o seu pedido.",
    )
    assert texto_mensagem not in caplog.text
    assert "987654321" not in caplog.text


def test_falha_ao_registrar_movimentacao_envia_fallback_seguro(caplog):
    bot, dependencias = preparar_handler()
    registro = RegistroFinanceiroFake()
    dependencias["interpretar_mensagem"].return_value = registro
    dependencias["registrar_movimentacao"].side_effect = RuntimeError("falha planilha")

    with caplog.at_level(logging.ERROR, logger="main"):
        bot.handler(criar_mensagem("gastei 30 no mercado em 15/09/2026"))

    dependencias["registrar_movimentacao"].assert_called_once_with(
        dependencias["planilha"], registro
    )
    dependencias["consultar_gastos_mes"].assert_not_called()
    assert bot.send_message.call_args_list[-1].args == (
        CHAT_ID,
        "Ops, ocorreu um erro ao processar o seu pedido.",
    )
    assert "gastei 30 no mercado em 15/09/2026" not in caplog.text
    assert "token-ficticio" not in caplog.text


def test_falha_ao_consultar_gastos_envia_fallback_seguro(caplog):
    bot, dependencias = preparar_handler()
    dependencias["interpretar_mensagem"].return_value = {
        "intencao": "consultar",
        "mes": "09",
        "ano": "2026",
    }
    dependencias["consultar_gastos_mes"].side_effect = RuntimeError("falha consulta")

    with caplog.at_level(logging.ERROR, logger="main"):
        bot.handler(criar_mensagem("quanto gastei em setembro?"))

    dependencias["consultar_gastos_mes"].assert_called_once_with(
        dependencias["planilha"], "09", "2026"
    )
    dependencias["registrar_movimentacao"].assert_not_called()
    assert bot.send_message.call_args_list[-1].args == (
        CHAT_ID,
        "Ops, ocorreu um erro ao processar o seu pedido.",
    )
    assert "quanto gastei em setembro?" not in caplog.text


def test_criar_bot_conecta_planilha_registra_handlers_e_nao_inicia_polling():
    bot = FakeBot()
    telebot_modulo = criar_modulo("telebot", TeleBot=Mock(return_value=bot))
    planilha = object()
    config_modulo = criar_modulo("financeirane.config", TELEGRAM_TOKEN="token-ficticio")
    sheets_modulo = criar_modulo(
        "financeirane.sheets_service", conectar_planilha=Mock(return_value=planilha)
    )

    with (
        patch.dict(
            sys.modules,
            {
                "telebot": telebot_modulo,
                "financeirane.config": config_modulo,
                "financeirane.sheets_service": sheets_modulo,
            },
        ),
        patch.object(telegram_bot, "registrar_handlers") as registrar_handlers,
    ):
        resultado = telegram_bot.criar_bot()

    assert resultado is bot
    sheets_modulo.conectar_planilha.assert_called_once_with()
    telebot_modulo.TeleBot.assert_called_once_with("token-ficticio")
    registrar_handlers.assert_called_once_with(bot, planilha)
    assert not hasattr(bot, "infinity_polling") or not bot.infinity_polling.called


def test_importar_main_nao_inicia_polling(monkeypatch):
    iniciar = Mock()
    monkeypatch.setattr(package_main, "main", iniciar)

    importlib.reload(main)

    iniciar.assert_not_called()


def test_package_main_configura_logging_cria_bot_e_inicia_polling(monkeypatch):
    bot = SimpleNamespace(infinity_polling=Mock())
    configurar_logging = Mock()
    criar_bot = Mock(return_value=bot)
    monkeypatch.setattr(package_main, "configurar_logging", configurar_logging)
    monkeypatch.setattr(package_main, "criar_bot", criar_bot)

    package_main.main()

    configurar_logging.assert_called_once_with()
    criar_bot.assert_called_once_with()
    bot.infinity_polling.assert_called_once_with()


def test_root_main_delega_para_package_main(monkeypatch):
    iniciar = Mock()
    monkeypatch.setattr(main.package_main, "main", iniciar)

    main.main()

    iniciar.assert_called_once_with()


def test_python_m_financeirane_delega_para_package_main(monkeypatch):
    iniciar = Mock()
    monkeypatch.setattr(package_main, "main", iniciar)

    runpy.run_module("financeirane", run_name="__main__")

    iniciar.assert_called_once_with()
