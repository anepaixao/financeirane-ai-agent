import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from gspread.exceptions import WorksheetNotFound
from requests.exceptions import Timeout

from financeirane.domain.compromissos import CompromissoFinanceiro
from financeirane.domain.exceptions import EntradaInvalidaError, FinanceiraneError
from financeirane.repositories.compromissos import (
    CompromissoIdentificado,
    CompromissoNaoEncontradoError,
)

ABA_COMPROMISSOS = "Compromissos"
CABECALHO = ["ID", "Descrição", "Valor", "Vencimento", "Tipo", "Status"]
FORMATO_VALOR = re.compile(r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}\Z")
FORMATO_DATA = re.compile(r"\d{2}/\d{2}/\d{4}\Z")


class RepositorioSheetsError(FinanceiraneError):
    pass


class DadosCompromissosInvalidosError(RepositorioSheetsError):
    pass


class CompromissoDuplicadoError(RepositorioSheetsError):
    pass


class CriacaoIndeterminadaError(RepositorioSheetsError):
    def __init__(self, identificador: UUID, erro_escrita: Timeout):
        super().__init__(
            "Criação sem confirmação após timeout; não houve nova tentativa."
        )
        self.identificador = identificador
        self.erro_escrita = erro_escrita


class RepositorioSheetsLeituraError(RepositorioSheetsError):
    pass


class RepositorioSheetsEscritaError(RepositorioSheetsError):
    pass


def serializar_compromisso(identificador: UUID, compromisso: CompromissoFinanceiro):
    valor = (
        f"{compromisso.valor:,.2f}".replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )
    return [
        str(identificador),
        compromisso.descricao,
        valor,
        compromisso.vencimento.strftime("%d/%m/%Y"),
        compromisso.tipo.value,
        compromisso.status.value,
    ]


def desserializar_compromisso(linha):
    if len(linha) != len(CABECALHO):
        raise DadosCompromissosInvalidosError("Linha de compromisso inválida.")
    try:
        identificador = UUID(linha[0])
        valor_texto = linha[2].replace("\u00a0", " ").strip()
        if valor_texto.startswith("R$"):
            valor_texto = valor_texto[2:].strip()
        if not FORMATO_VALOR.fullmatch(valor_texto) or not FORMATO_DATA.fullmatch(
            linha[3]
        ):
            raise ValueError("Formato inválido")
        valor = Decimal(valor_texto.replace(".", "").replace(",", "."))
        vencimento = datetime.strptime(linha[3], "%d/%m/%Y").date()
        compromisso = CompromissoFinanceiro(
            descricao=linha[1],
            valor=valor,
            vencimento=vencimento,
            tipo=linha[4],
            status=linha[5],
        )
    except (ValueError, TypeError, EntradaInvalidaError) as exc:
        raise DadosCompromissosInvalidosError(
            "Dados de compromisso inválidos na planilha."
        ) from exc
    return CompromissoIdentificado(identificador, compromisso)


class RepositorioCompromissosSheets:
    def __init__(self, planilha):
        try:
            self._aba = planilha.worksheet(ABA_COMPROMISSOS)
        except WorksheetNotFound as exc:
            raise DadosCompromissosInvalidosError(
                "A aba Compromissos não existe."
            ) from exc
        except Exception as exc:
            raise RepositorioSheetsLeituraError(
                "Falha ao selecionar a aba Compromissos."
            ) from exc

    def _ler(self):
        try:
            linhas = self._aba.get_all_values(value_render_option="FORMATTED_VALUE")
        except Exception as exc:
            raise RepositorioSheetsLeituraError("Falha ao ler compromissos.") from exc
        if not isinstance(linhas, list) or not linhas or linhas[0] != CABECALHO:
            raise DadosCompromissosInvalidosError(
                "Cabeçalho da aba Compromissos inválido."
            )
        encontrados = {}
        for numero_linha, linha in enumerate(linhas[1:], start=2):
            if not isinstance(linha, list):
                raise DadosCompromissosInvalidosError(
                    "Estrutura de linha de compromisso inválida."
                )
            if not linha or all(celula == "" for celula in linha):
                continue
            identificado = desserializar_compromisso(linha)
            if identificado.identificador in encontrados:
                raise CompromissoDuplicadoError(
                    "Identificador de compromisso duplicado na planilha."
                )
            encontrados[identificado.identificador] = (numero_linha, identificado)
        return encontrados

    @staticmethod
    def _validar_identificador(identificador):
        if not isinstance(identificador, UUID):
            raise EntradaInvalidaError("Identificador do compromisso inválido.")

    @staticmethod
    def _validar_compromisso(compromisso):
        if not isinstance(compromisso, CompromissoFinanceiro):
            raise EntradaInvalidaError("Compromisso financeiro inválido.")

    def salvar(self, compromisso: CompromissoFinanceiro) -> CompromissoIdentificado:
        self._validar_compromisso(compromisso)
        existentes = self._ler()
        identificador = uuid4()
        while identificador in existentes:
            identificador = uuid4()
        linha = serializar_compromisso(identificador, compromisso)
        try:
            self._aba.append_row(linha, value_input_option="RAW")
        except Timeout as exc:
            try:
                encontrados = self._ler()
            except RepositorioSheetsLeituraError as erro_leitura:
                raise CriacaoIndeterminadaError(
                    identificador, erro_escrita=exc
                ) from erro_leitura
            if identificador in encontrados:
                identificado = encontrados[identificador][1]
                if identificado.compromisso != compromisso:
                    raise DadosCompromissosInvalidosError(
                        "Compromisso recuperado após timeout diverge do enviado."
                    ) from exc
                return identificado
            raise CriacaoIndeterminadaError(identificador, erro_escrita=exc) from exc
        except Exception as exc:
            raise RepositorioSheetsEscritaError("Falha ao criar compromisso.") from exc
        return CompromissoIdentificado(identificador, compromisso)

    def buscar(self, identificador: UUID) -> CompromissoIdentificado:
        self._validar_identificador(identificador)
        encontrados = self._ler()
        try:
            return encontrados[identificador][1]
        except KeyError as exc:
            raise CompromissoNaoEncontradoError("Compromisso não encontrado.") from exc

    def listar(self) -> list[CompromissoIdentificado]:
        return [identificado for _, identificado in self._ler().values()]

    def atualizar(
        self, identificador: UUID, compromisso: CompromissoFinanceiro
    ) -> CompromissoIdentificado:
        self._validar_identificador(identificador)
        self._validar_compromisso(compromisso)
        for _ in range(2):
            encontrados = self._ler()
            if identificador not in encontrados:
                raise CompromissoNaoEncontradoError("Compromisso não encontrado.")
            numero_linha = encontrados[identificador][0]
            try:
                id_na_linha = self._aba.cell(numero_linha, 1).value
            except Exception as exc:
                raise RepositorioSheetsLeituraError(
                    "Falha ao conferir identificador antes da atualização."
                ) from exc
            if id_na_linha == str(identificador):
                linha = serializar_compromisso(identificador, compromisso)
                try:
                    self._aba.update(
                        range_name=f"A{numero_linha}:F{numero_linha}",
                        values=[linha],
                        value_input_option="RAW",
                    )
                except Exception as exc:
                    raise RepositorioSheetsEscritaError(
                        "Falha ao atualizar compromisso."
                    ) from exc
                return CompromissoIdentificado(identificador, compromisso)
        raise DadosCompromissosInvalidosError(
            "A posição do compromisso mudou durante a atualização."
        )
