import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import main

AUTHORIZED_USER_ID = 123456789
CHAT_ID = 987654321
MAX_MESSAGE_LENGTH = 10


class FakeBot:
    def __init__(self):
        self.handler = None
        self.send_message = Mock()

    def message_handler(self, **_kwargs):
        def decorator(func):
            self.handler = func
            return func

        return decorator


class RegistroFinanceiroFake:
    pass


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
    dependencias = {
        "interpretar_mensagem": Mock(name="interpretar_mensagem"),
        "registrar_movimentacao": Mock(name="registrar_movimentacao"),
        "consultar_gastos_mes": Mock(name="consultar_gastos_mes"),
    }

    modulos = {
        "ai_service": criar_modulo(
            "ai_service", interpretar_mensagem=dependencias["interpretar_mensagem"]
        ),
        "config": criar_modulo(
            "config",
            AUTHORIZED_CHAT_IDS={AUTHORIZED_USER_ID},
            MAX_MESSAGE_LENGTH=MAX_MESSAGE_LENGTH,
        ),
        "models": criar_modulo("models", RegistroFinanceiro=RegistroFinanceiroFake),
        "sheets_service": criar_modulo(
            "sheets_service",
            consultar_gastos_mes=dependencias["consultar_gastos_mes"],
            registrar_movimentacao=dependencias["registrar_movimentacao"],
        ),
    }

    bot = FakeBot()
    planilha = object()

    with patch.dict(sys.modules, modulos):
        main.registrar_handlers(bot, planilha)

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


def test_comando_id_responde_ids_do_usuario_e_chat():
    bot, dependencias = preparar_handler()

    bot.handler(criar_mensagem("/id"))

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
