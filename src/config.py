import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent  


@dataclass
class Config:
    url_login: str
    url_produtos: str
    preco_venda: str
    quantidade: str
    consignado: bool
    estado: str
    vender_no_pdv: bool
    categorias: dict
    pasta_dados: Path
    email: str = ""
    senha: str = field(default="", repr=False)  

    @property
    def fotos(self):
        return self.pasta_dados / "fotos"

    @property
    def cadastrados(self):
        return self.fotos / "cadastrados"

    @property
    def erros(self):
        return self.pasta_dados / "erros"

    @property
    def produtos_json(self):
        return self.pasta_dados / "produtos.json"

    @property
    def relatorio_json(self):
        return self.pasta_dados / "relatorio_cadastro.json"


def carregar(root=ROOT):
    with open(root / "configs" / "settings.yaml", encoding="utf-8") as f:
        s = yaml.safe_load(f)

    dados = os.getenv("LOJINHA_DADOS", "").strip()
    return Config(
        url_login=s["site"]["login"],
        url_produtos=s["site"]["produtos"],
        preco_venda=str(s["cadastro"]["preco_venda"]),
        quantidade=str(s["cadastro"]["quantidade"]),
        consignado=bool(s["cadastro"]["consignado"]),
        estado=s["cadastro"]["estado"],
        vender_no_pdv=bool(s["cadastro"]["vender_no_pdv"]),
        categorias=s["categorias"],
        pasta_dados=Path(dados) if dados else root/ "dados",
        email=os.getenv("LOJA_EMAIL", "").strip(),
        senha=os.getenv("LOJA_SENHA", ""),
    )
