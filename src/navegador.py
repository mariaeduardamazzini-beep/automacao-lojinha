"""Tudo que conversa com o site (Playwright): login, Cadastro Express e conferência."""

import re
import time
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from textos import escolher_opcao, sem_acento

FORM = "#nomeProdutoExpress"
MODAL = "#cadastroExpressModal"


class Navegador:
    """Uso:  with Navegador(config) as nav:  nav.login(...); nav.cadastrar(...)"""

    def __init__(self, config):
        self.config = config
        self.page = None

    # === abrir e fechar o navegador ===
    def __enter__(self):
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(channel="chrome", headless=False, args=["--start-maximized"])
        except Exception:
            self._browser = self._pw.chromium.launch(headless=False, args=["--start-maximized"])
        self.page = self._browser.new_context(no_viewport=True).new_page()
        self.page.set_default_timeout(15000)
        return self

    def __exit__(self, *erro):
        self._browser.close()
        self._pw.stop()

    # === navegação ===
    def fechar_popups(self):
        for _ in range(3):
            botao = self.page.get_by_text("Agora não")
            try:
                if botao.count() and botao.first.is_visible():
                    botao.first.click()
                    self.page.wait_for_timeout(800)
                    continue
            except Exception:
                pass
            break

    def login(self, email, senha):
        print("-> Fazendo login...")
        p = self.page
        p.goto(self.config.url_login)
        p.wait_for_timeout(4000)
        self.fechar_popups()
        p.locator("input[type='email'], input[placeholder*='mail' i]").first.fill(email)
        p.locator("input[type='password']").first.fill(senha)
        p.get_by_role("button", name=re.compile("entrar", re.I)).first.click()
        p.wait_for_timeout(5000)
        senha_visivel = p.locator("input[type='password']")
        if senha_visivel.count() and senha_visivel.first.is_visible():
            raise Exception("O login não funcionou. Necessário conferir e-mail e senha.")
        print("-> Login ok.")

    def ir_para_produtos(self):
        self.page.goto(self.config.url_produtos)
        self.page.locator("#btnAbrirSelecaoCadastro").wait_for(state="visible", timeout=40000)
        self.page.wait_for_timeout(1500)
        self.fechar_popups()

    def salvar_print(self, nome):
        try:
            self.config.erros.mkdir(parents=True, exist_ok=True)
            arquivo = self.config.erros / f"erro_{sem_acento(nome)}.png"
            self.page.screenshot(path=str(arquivo))
            print(f"-> Print do erro salvo em: {arquivo}")
        except Exception:
            pass

    # === abrir o formulário ===
    def _form_visivel(self, timeout=1500):
        try:
            self.page.locator(FORM).wait_for(state="visible", timeout=timeout)
            return True
        except PWTimeout:
            return False

    def _iguais_marcado(self):
        """True se 'Tratar todas as peças como iguais' já estiver marcado no site."""
        try:
            card = self.page.locator(f'{MODAL} .option-card[data-value="unico"]').first
            if "selected" in (card.get_attribute("class") or ""):
                return True
            radio = self.page.locator(f"{MODAL} #tipoCadastroUnico")
            return radio.count() > 0 and radio.first.is_checked()
        except Exception:
            return False

    def _abrir_formulario(self):
        """Novo Produto -> Cadastro Express -> Início -> Tipo de Estoque -> Dados do Produto."""
        p = self.page
        if self._form_visivel():
            return
        if not (p.locator(MODAL).count() and p.locator(MODAL).is_visible()):
            self.fechar_popups()
            p.locator("#btnAbrirSelecaoCadastro").click()
            p.locator("#cardCadastroExpress").click()
            p.locator(MODAL).wait_for(state="visible", timeout=10000)
            p.wait_for_timeout(1000)
        for _ in range(6):
            if self._form_visivel():
                return
            iguais = p.locator(f'{MODAL} .option-card[data-value="unico"]')
            if iguais.count() and iguais.first.is_visible():  # etapa "Tipo de Estoque"
                if not self._iguais_marcado():  # clicar de novo DESMARCA, por isso confere antes
                    iguais.first.click()
                    p.wait_for_timeout(700)
                if not self._iguais_marcado():
                    continue
            avancar = p.locator(f"{MODAL} #btnNext")
            if avancar.count() and avancar.first.is_visible():
                avancar.first.click()
            if self._form_visivel(4000):
                return
        raise Exception("O formulário 'Dados do Produto' não apareceu.")

    # === campos do formulário ===
    def _escolher_select2(self, campo, texto):
        """Abre a lista, clica na opção PELO TEXTO e confere o resultado."""
        p = self.page
        alvo = sem_acento(texto)
        ultimo_erro = ""
        for tentativa in (1, 2, 3):
            p.locator(f"#select2-{campo}-container").click()
            fim, inicio_lista, escolhido, vistos = time.time() + 10, None, None, []
            while time.time() < fim and escolhido is None:
                textos = [t.strip() for t in p.locator("li.select2-results__option").all_inner_texts()]
                vistos = [t for t in textos if t and sem_acento(t) not in ("buscando", "carregando", "nenhumresultadoencontrado")]
                if vistos:
                    inicio_lista = inicio_lista or time.time()
                    pos = escolher_opcao(vistos, alvo, aproximado=time.time() - inicio_lista > 3)
                    if pos is not None:
                        escolhido = vistos[pos]
                if escolhido is None:
                    p.wait_for_timeout(500)
            if escolhido is None:
                p.keyboard.press("Escape")
                ultimo_erro = f"Opção '{texto}' não apareceu em '{campo}'. Opções vistas: {vistos}"
                continue
            p.locator("li.select2-results__option").filter(
                has_text=re.compile(rf"^\s*{re.escape(escolhido)}\s*$")).first.click(timeout=5000)
            p.wait_for_timeout(800)
            mostrado = p.locator(f"#select2-{campo}-container").inner_text().strip()
            if sem_acento(mostrado) == sem_acento(escolhido):
                return escolhido
            ultimo_erro = f"Foi clicado em '{escolhido}', mas o campo ficou com '{mostrado}'."
            print(f"-> {ultimo_erro} Tentando de novo ({tentativa}/3)...")
        raise Exception(ultimo_erro)

    def _preencher_preco(self, valor):
        campo = self.page.locator("#precoVendaProduto")
        alvo = re.sub(r"\D", "", valor)  # "5,00" -> "500"
        for tentativa in (alvo, valor):
            campo.click()
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")
            campo.press_sequentially(tentativa, delay=60)
            if re.sub(r"\D", "", campo.input_value()) == alvo:  # o site mostra "R$ 5,00"
                return
        raise Exception(f"Preço ficou '{campo.input_value()}' em vez de '{valor}'.")

    def _subir_foto(self, foto):
        p = self.page
        if not foto.is_file():
            raise Exception(f"Arquivo da foto não existe: {foto}")
        p.evaluate("""() => {  // remove foto que sobrou do produto anterior
            const r = document.querySelector('#cadastroExpressModal .filepond--root');
            if (r && window.FilePond) { const f = FilePond.find(r); if (f) f.removeFiles({revert: false}); }
        }""")
        p.wait_for_timeout(800)
        p.locator(f"{MODAL} input[type='file']").first.set_input_files(str(foto.resolve()))
        try:
            estado = p.wait_for_function("""() => {
                const itens = [...document.querySelectorAll('#cadastroExpressModal .filepond--item')];
                if (!itens.length) return false;
                const st = itens.map(i => i.getAttribute('data-filepond-item-state') || '');
                if (st.some(s => /error|invalid/.test(s))) return 'ERRO:' + st.join(',');
                if (st.every(s => s === 'idle' || s === 'processing-complete')) return 'ok:' + st.length;
                return false;
            }""", timeout=40000).json_value()
        except PWTimeout as e:
            raise Exception("A foto não apareceu no formulário depois do envio.") from e
        if estado != "ok:1":
            raise Exception(f"Problema com a foto no formulário ({estado}).")
        p.wait_for_timeout(1000)

    def _esperar_sucesso(self):
        try:
            resposta = self.page.wait_for_function("""() => {
                const pop = [...document.querySelectorAll('.swal2-popup')].find(e => getComputedStyle(e).display !== 'none');
                if (!pop) return false;
                const t = (pop.innerText || '').toLowerCase();
                if (t.includes('cadastrado com sucesso')) return 'ok';
                if (/erro|ops|aten[cç][aã]o|preencha|obrigat|inv[aá]lid/.test(t)) return 'MSG:' + pop.innerText.replace(/\\n/g, ' ');
                return false;
            }""", timeout=45000).json_value()
        except PWTimeout as e:
            raise Exception("A confirmação 'Produto cadastrado com sucesso!' não apareceu.") from e
        if resposta != "ok":
            raise Exception(f"O site mostrou um aviso: {resposta}")

    #  o que o programa usa 
    def cadastrar(self, produto, ultimo):
        """Cadastra apenas >> UM << produto. Levanta Exception se algo não for confirmado pelo site."""
        c, p = self.config, self.page
        print(f"\n-> Cadastrando: {produto.nome}  [{produto.categoria} > {produto.subcategoria}]")
        self._abrir_formulario()
        p.locator(FORM).fill(produto.nome)
        p.select_option("#eConsignadoCadastroExpress", value="1" if c.consignado else "0")
        p.select_option("#estadoProdutoExpress", label=c.estado)
        p.locator("#venderPDVExpress").set_checked(c.vender_no_pdv, force=True)
        self._escolher_select2("categoriaProduto", produto.categoria)
        p.wait_for_function("() => { const s = document.querySelector('#subcategoriaProduto'); return s && !s.disabled; }", timeout=15000)
        p.wait_for_timeout(1000)
        self._escolher_select2("subcategoriaProduto", produto.subcategoria)
        self._preencher_preco(c.preco_venda)  # preço de compra fica vazio
        p.locator("#qtdPecasProduto").fill(c.quantidade)
        self._subir_foto(produto.foto)
        p.locator(f"{MODAL} #btnNext").click()
        self._esperar_sucesso()
        print(f"✅ {produto.nome} cadastrado (confirmado pelo site).")
        botao = "Não, ir para produtos" if ultimo else "Sim, cadastrar outro"
        p.get_by_role("button", name=re.compile(re.escape(botao), re.I)).click()
        p.wait_for_timeout(2500)

    def conferir(self, nomes, inicio):
        """Procura cada nome na lista de Produtos."""
        print("\n-> Conferindo na lista de produtos...")
        resultado = {}
        try:
            self.ir_para_produtos()
            busca = self.page.locator("#dt-search-0")
            busca.wait_for(state="visible", timeout=25000)
            limite = inicio - timedelta(minutes=10)
            for nome in nomes:
                busca.fill(nome)
                self.page.wait_for_timeout(2000)
                resultado[nome] = "nao"
                for linha in self.page.locator("#tableProdutos tbody tr").all_text_contents():
                    if sem_acento(nome) not in sem_acento(linha):
                        continue
                    data = re.search(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2})", linha)
                    if not data or datetime.strptime(data.group(1), "%d/%m/%Y %H:%M") >= limite:
                        resultado[nome] = "ok"
                        break
                    resultado[nome] = "antigo"
        except Exception as e:
            print("-> Não foi possível concluir a conferência:", e)
            self.salvar_print("conferencia")
        return resultado
