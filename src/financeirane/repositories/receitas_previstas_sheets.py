import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from gspread.exceptions import WorksheetNotFound
from requests.exceptions import Timeout

from financeirane.domain.exceptions import EntradaInvalidaError, FinanceiraneError
from financeirane.domain.receitas_previstas import ReceitaPrevista
from financeirane.repositories.receitas_previstas import (
    ReceitaPrevistaIdentificada,
    ReceitaPrevistaNaoEncontradaError,
)

ABA_RECEITAS_PREVISTAS = "Receitas Previstas"
CABECALHO = ["ID", "Descrição", "Valor previsto", "Data prevista", "Status"]
FORMATO_VALOR = re.compile(r"(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2}\Z")
FORMATO_DATA = re.compile(r"\d{2}/\d{2}/\d{4}\Z")


class RepositorioReceitasPrevistasSheetsError(FinanceiraneError):
    pass


class DadosReceitasPrevistasInvalidosError(RepositorioReceitasPrevistasSheetsError):
    pass


class ReceitaPrevistaDuplicadaError(RepositorioReceitasPrevistasSheetsError):
    pass


class CriacaoReceitaIndeterminadaError(RepositorioReceitasPrevistasSheetsError):
    def __init__(self, identificador: UUID, erro_escrita: Timeout):
        super().__init__(
            "Criação sem confirmação após timeout; não houve nova tentativa."
        )
        self.identificador = identificador
        self.erro_escrita = erro_escrita


class RepositorioReceitasSheetsLeituraError(RepositorioReceitasPrevistasSheetsError):
    pass


class RepositorioReceitasSheetsEscritaError(RepositorioReceitasPrevistasSheetsError):
    pass


def serializar_receita(identificador: UUID, receita: ReceitaPrevista):
    valor = (
        f"{receita.valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return [
        str(identificador),
        receita.descricao,
        valor,
        receita.data_prevista.strftime("%d/%m/%Y"),
        receita.status.value,
    ]


def desserializar_receita(linha):
    if len(linha) != len(CABECALHO):
        raise DadosReceitasPrevistasInvalidosError(
            "Linha de receita prevista inválida."
        )
    try:
        identificador = UUID(linha[0])
        valor_texto = linha[2].replace("\u00a0", " ").strip()
        if valor_texto.startswith("R$"):
            valor_texto = valor_texto[2:].strip()
        if not FORMATO_VALOR.fullmatch(valor_texto) or not FORMATO_DATA.fullmatch(
            linha[3]
        ):
            raise ValueError("Formato inválido")
        receita = ReceitaPrevista(
            descricao=linha[1],
            valor=Decimal(valor_texto.replace(".", "").replace(",", ".")),
            data_prevista=datetime.strptime(linha[3], "%d/%m/%Y").date(),
            status=linha[4],
        )
    except (ValueError, TypeError, EntradaInvalidaError) as exc:
        raise DadosReceitasPrevistasInvalidosError(
            "Dados de receita prevista inválidos na planilha."
        ) from exc
    return ReceitaPrevistaIdentificada(identificador, receita)


class RepositorioReceitasPrevistasSheets:
    """Adaptador para um único escritor; Sheets não atualiza por UUID atomicamente."""

    def __init__(self, planilha):
        try:
            self._aba = planilha.worksheet(ABA_RECEITAS_PREVISTAS)
        except WorksheetNotFound as exc:
            raise DadosReceitasPrevistasInvalidosError(
                "A aba Receitas Previstas não existe."
            ) from exc
        except Exception as exc:
            raise RepositorioReceitasSheetsLeituraError(
                "Falha ao selecionar a aba Receitas Previstas."
            ) from exc

    def _ler(self):
        try:
            linhas = self._aba.get_all_values(value_render_option="FORMATTED_VALUE")
        except Exception as exc:
            raise RepositorioReceitasSheetsLeituraError(
                "Falha ao ler receitas previstas."
            ) from exc
        if not isinstance(linhas, list) or not linhas or linhas[0] != CABECALHO:
            raise DadosReceitasPrevistasInvalidosError(
                "Cabeçalho da aba Receitas Previstas inválido."
            )
        encontrados = {}
        for numero_linha, linha in enumerate(linhas[1:], start=2):
            if not isinstance(linha, list):
                raise DadosReceitasPrevistasInvalidosError(
                    "Estrutura de linha de receita prevista inválida."
                )
            if not linha or all(celula == "" for celula in linha):
                continue
            identificada = desserializar_receita(linha)
            if identificada.identificador in encontrados:
                raise ReceitaPrevistaDuplicadaError(
                    "Identificador de receita prevista duplicado na planilha."
                )
            encontrados[identificada.identificador] = (numero_linha, identificada)
        return encontrados

    @staticmethod
    def _validar_identificador(identificador):
        if not isinstance(identificador, UUID):
            raise EntradaInvalidaError("Identificador da receita prevista inválido.")

    @staticmethod
    def _validar_receita(receita):
        if not isinstance(receita, ReceitaPrevista):
            raise EntradaInvalidaError("Receita prevista inválida.")

    def salvar(self, receita: ReceitaPrevista) -> ReceitaPrevistaIdentificada:
        self._validar_receita(receita)
        existentes = self._ler()
        identificador = uuid4()
        while identificador in existentes:
            identificador = uuid4()
        linha = serializar_receita(identificador, receita)
        try:
            self._aba.append_row(linha, value_input_option="RAW")
        except Timeout as exc:
            try:
                encontrados = self._ler()
            except (
                RepositorioReceitasSheetsLeituraError,
                DadosReceitasPrevistasInvalidosError,
            ) as erro_leitura:
                raise CriacaoReceitaIndeterminadaError(
                    identificador, erro_escrita=exc
                ) from erro_leitura
            if identificador in encontrados:
                identificada = encontrados[identificador][1]
                if identificada.receita != receita:
                    raise DadosReceitasPrevistasInvalidosError(
                        "Receita recuperada após timeout diverge da enviada."
                    ) from exc
                return identificada
            raise CriacaoReceitaIndeterminadaError(
                identificador, erro_escrita=exc
            ) from exc
        except Exception as exc:
            raise RepositorioReceitasSheetsEscritaError(
                "Falha ao criar receita prevista."
            ) from exc
        return ReceitaPrevistaIdentificada(identificador, receita)

    def buscar(self, identificador: UUID) -> ReceitaPrevistaIdentificada:
        self._validar_identificador(identificador)
        encontrados = self._ler()
        try:
            return encontrados[identificador][1]
        except KeyError as exc:
            raise ReceitaPrevistaNaoEncontradaError(
                "Receita prevista não encontrada."
            ) from exc

    def listar(self) -> list[ReceitaPrevistaIdentificada]:
        return [identificada for _, identificada in self._ler().values()]

    def atualizar(
        self, identificador: UUID, receita: ReceitaPrevista
    ) -> ReceitaPrevistaIdentificada:
        self._validar_identificador(identificador)
        self._validar_receita(receita)
        for _ in range(2):
            encontrados = self._ler()
            if identificador not in encontrados:
                raise ReceitaPrevistaNaoEncontradaError(
                    "Receita prevista não encontrada."
                )
            numero_linha = encontrados[identificador][0]
            try:
                id_na_linha = self._aba.cell(numero_linha, 1).value
            except Exception as exc:
                raise RepositorioReceitasSheetsLeituraError(
                    "Falha ao conferir identificador antes da atualização."
                ) from exc
            if id_na_linha == str(identificador):
                linha = serializar_receita(identificador, receita)
                try:
                    self._aba.update(
                        range_name=f"A{numero_linha}:E{numero_linha}",
                        values=[linha],
                        value_input_option="RAW",
                    )
                except Exception as exc:
                    raise RepositorioReceitasSheetsEscritaError(
                        "Falha ao atualizar receita prevista."
                    ) from exc
                return ReceitaPrevistaIdentificada(identificador, receita)
        raise DadosReceitasPrevistasInvalidosError(
            "A posição da receita prevista mudou durante a atualização."
        )
