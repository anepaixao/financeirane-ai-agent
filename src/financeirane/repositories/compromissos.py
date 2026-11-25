from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from financeirane.domain.compromissos import CompromissoFinanceiro
from financeirane.domain.exceptions import EntradaInvalidaError, FinanceiraneError


class CompromissoNaoEncontradoError(FinanceiraneError):
    pass


@dataclass(frozen=True)
class CompromissoIdentificado:
    identificador: UUID
    compromisso: CompromissoFinanceiro


class RepositorioCompromissos(Protocol):
    """salvar cria um registro novo; atualizar substitui pelo identificador."""

    def salvar(self, compromisso: CompromissoFinanceiro) -> CompromissoIdentificado: ...

    def buscar(self, identificador: UUID) -> CompromissoIdentificado: ...

    def listar(self) -> list[CompromissoIdentificado]: ...

    def atualizar(
        self, identificador: UUID, compromisso: CompromissoFinanceiro
    ) -> CompromissoIdentificado: ...


class RepositorioCompromissosEmMemoria:
    def __init__(self):
        self._compromissos: dict[UUID, CompromissoFinanceiro] = {}

    def salvar(self, compromisso: CompromissoFinanceiro) -> CompromissoIdentificado:
        self._validar_compromisso(compromisso)
        identificador = uuid4()
        while identificador in self._compromissos:
            identificador = uuid4()
        self._compromissos[identificador] = compromisso
        return CompromissoIdentificado(identificador, compromisso)

    def buscar(self, identificador: UUID) -> CompromissoIdentificado:
        self._validar_identificador(identificador)
        try:
            compromisso = self._compromissos[identificador]
        except KeyError as exc:
            raise CompromissoNaoEncontradoError("Compromisso não encontrado.") from exc
        return CompromissoIdentificado(identificador, compromisso)

    def listar(self) -> list[CompromissoIdentificado]:
        return [
            CompromissoIdentificado(identificador, compromisso)
            for identificador, compromisso in self._compromissos.items()
        ]

    def atualizar(
        self, identificador: UUID, compromisso: CompromissoFinanceiro
    ) -> CompromissoIdentificado:
        self.buscar(identificador)
        self._validar_compromisso(compromisso)
        self._compromissos[identificador] = compromisso
        return CompromissoIdentificado(identificador, compromisso)

    @staticmethod
    def _validar_identificador(identificador: UUID):
        if not isinstance(identificador, UUID):
            raise EntradaInvalidaError("Identificador do compromisso inválido.")

    @staticmethod
    def _validar_compromisso(compromisso: CompromissoFinanceiro):
        if not isinstance(compromisso, CompromissoFinanceiro):
            raise EntradaInvalidaError("Compromisso financeiro inválido.")
