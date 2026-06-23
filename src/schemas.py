"""Schema Pydantic dos 5 campos do TRCT (response_format para o Experimento B)."""

from pydantic import BaseModel, Field


class ExtracaoTRCT(BaseModel):
    nome_trabalhador: str = Field(default="", description="Campo 11 (Nome) — nome completo do trabalhador.")
    nome_empregador: str = Field(default="", description="Campo 02 (Razão Social/Nome) — nome/razão social do empregador.")
    # string de propósito: o modelo devolve como no formulário; o float fica com o comparador
    ultima_remuneracao: str = Field(default="", description="Campo 23 (Remuneração Mês Ant.), ex.: '1.843,25'.")
    data_admissao: str = Field(default="", description="Campo 24 (Data de Admissão), dd/mm/aaaa.")
    data_demissao: str = Field(default="", description="Campo 26 (Data de Afastamento), dd/mm/aaaa.")
