from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from financeirane.domain.exceptions import EntradaInvalidaError, FinanceiraneError
from financeirane.domain.receitas_previstas import ReceitaPrevista


class ReceitaPrevistaNaoEncontradaError(FinanceiraneError):
    pass


@dataclass(frozen=True)
class ReceitaPrevistaIdentificada:
    identificador: UUID
    receita: ReceitaPrevista


class RepositorioReceitasPrevistas(Protocol):
    """salvar cria uma ocorrência nova; atualizar substitui pelo identificador."""

    def salvar(self, receita: ReceitaPrevista) -> ReceitaPrevistaIdentificada: ...

    def buscar(self, identificador: UUID) -> ReceitaPrevistaIdentificada: ...

    def listar(self) -> list[ReceitaPrevistaIdentificada]: ...

    def atualizar(
        self, identificador: UUID, receita: ReceitaPrevista
    ) -> ReceitaPrevistaIdentificada: ...


class RepositorioReceitasPrevistasEmMemoria:
    def __init__(self):
        self._receitas: dict[UUID, ReceitaPrevista] = {}

    def salvar(self, receita: ReceitaPrevista) -> ReceitaPrevistaIdentificada:
        self._validar_receita(receita)
        identificador = uuid4()
        while identificador in self._receitas:
            identificador = uuid4()
        self._receitas[identificador] = receita
        return ReceitaPrevistaIdentificada(identificador, receita)

    def buscar(self, identificador: UUID) -> ReceitaPrevistaIdentificada:
        self._validar_identificador(identificador)
        try:
            receita = self._receitas[identificador]
        except KeyError as exc:
            raise ReceitaPrevistaNaoEncontradaError(
                "Receita prevista não encontrada."
            ) from exc
        return ReceitaPrevistaIdentificada(identificador, receita)

    def listar(self) -> list[ReceitaPrevistaIdentificada]:
        return [
            ReceitaPrevistaIdentificada(identificador, receita)
            for identificador, receita in self._receitas.items()
        ]

    def atualizar(
        self, identificador: UUID, receita: ReceitaPrevista
    ) -> ReceitaPrevistaIdentificada:
        self.buscar(identificador)
        self._validar_receita(receita)
        self._receitas[identificador] = receita
        return ReceitaPrevistaIdentificada(identificador, receita)

    @staticmethod
    def _validar_identificador(identificador: UUID):
        if not isinstance(identificador, UUID):
            raise EntradaInvalidaError("Identificador da receita prevista inválido.")

    @staticmethod
    def _validar_receita(receita: ReceitaPrevista):
        if not isinstance(receita, ReceitaPrevista):
            raise EntradaInvalidaError("Receita prevista inválida.")
