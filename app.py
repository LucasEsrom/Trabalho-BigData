"""Painel de zoonoses: tratamento com pandas e interface com Streamlit."""
import io
import json
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Painel de Zoonoses", page_icon="🐾", layout="wide")
with st.container(key="menu_superior"):
    marca, navegacao, tema = st.columns([1, 9, 1])
    marca.markdown("**◈ Zoonoses**")
    pagina = navegacao.radio("Navegação", ["Visão geral", "Animais", "Vacinação", "Canil", "Notificações", "Diagnósticos", "Maus-tratos", "Óbitos e eutanásias", "Gerenciar dados"], horizontal=True, label_visibility="collapsed", key="pagina")
    noturno = tema.toggle("☾ Tema", key="modo_noturno", value=True)
paleta = {"fundo": "#0c1510", "cartao": "#15221a", "texto": "#e7f2ea", "suave": "#8fa797", "linha": "#2b4433", "verde": "#4fcf7d", "apoio": "#1a2b20"} if noturno else {"fundo": "#eaf3ec", "cartao": "#ffffff", "texto": "#12301f", "suave": "#5b7263", "linha": "#dbe8de", "verde": "#1b7437", "apoio": "#f3f9f4"}
variaveis = ":root{" + ";".join(f"--{k}:{v}" for k, v in paleta.items()) + "}"
st.markdown("<style>" + variaveis + Path(__file__).with_name("painel.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
CORES = ["#1b7437", "#e8b02f", "#2a9d8f", "#5fa3d6", "#d4574e", "#8e7cc3"]
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
ROTULOS = {"id": "Código", "ia": "Código do animal", "m": "Município", "e": "Espécie", "r": "Raça", "x": "Sexo", "i": "Idade", "d": "Data", "st": "Situação", "vf": "Vacinas faltantes", "sv": "Situação vacinal", "n": "Doses", "s": "Situação", "a": "Atendimento", "b": "Bairro", "t": "Tipo de ocorrência", "do": "Doença", "tr": "Tratamento", "ev": "Evolução", "tm": "Tipo de maus-tratos", "gr": "Gravidade", "pv": "Providências", "ot": "Tipo de ocorrência", "mo": "Motivo"}
contador_graficos = 0
secao_grafico = "resumo"
FILTROS_GRAFICOS = {"m": "Município", "e": "Espécie", "r": "Raça", "x": "Sexo", "s": "Situação no canil", "a": "Atendimento", "t": "Tipo de notificação", "b": "Bairro", "do": "Doença", "tm": "Tipo de maus-tratos", "gr": "Gravidade", "ot": "Óbito / Eutanásia"}


def selecionar_grafico(chave, filtro):
    """O callback ocorre antes da reconstrução dos filtros da página."""
    pontos = st.session_state.get(chave, {}).get("selection", {}).get("points", [])
    valores = list(dict.fromkeys(p["customdata"][0] for p in pontos if p.get("customdata")))
    st.session_state["f_" + filtro] = valores


def limpar_filtros():
    for chave in list(st.session_state):
        if chave.startswith("f_") or chave.startswith("busca_"):
            del st.session_state[chave]
    st.session_state["versao_graficos"] = st.session_state.get("versao_graficos", 0) + 1


def selecionar_todos(chave, opcoes):
    if "Selecionar todos" in st.session_state.get(chave, []):
        st.session_state[chave] = opcoes


def titulo_secao(titulo, descricao=""):
    st.markdown(f'<div class="titulo-secao"><h2>{escape(titulo)}</h2><p>{escape(descricao)}</p></div>', unsafe_allow_html=True)


def cartao(coluna, titulo, valor, detalhe="", icone="◇"):
    coluna.markdown(f'<div class="indicador"><div class="icone-indicador">{icone}</div><div class="rotulo-indicador">{escape(titulo)}</div><div class="valor-indicador">{escape(str(valor))}</div><div class="detalhe-indicador">{escape(detalhe)}</div></div>', unsafe_allow_html=True)


def numero(valor):
    return f"{int(valor):,}".replace(",", ".")


def indicadores_secao(chave, df):
    quantidade = len(df)
    municipios = df["m"].nunique()
    def percentual(campo, valor):
        return f"{df[campo].eq(valor).mean():.1%}".replace(".", ",") if quantidade else "Sem dados"
    extras = {
        "cad": [("Vacinação completa", percentual("sv", "Completa"), "Situação registrada no cadastro"),
                ("Idade média", f'{df["i"].mean():.1f}'.replace(".", ",") if df["i"].notna().any() else "Sem dados", "Entre os animais com idade informada")],
    } if chave == "cad" else {}
    if chave == "vac":
        extras[chave] = [("Doses aplicadas", numero(df["n"].sum()), "Soma das doses registradas"), ("Média por aplicação", f'{df["n"].mean():.1f}'.replace(".", ",") if quantidade else "Sem dados", "Doses por registro de vacinação")]
    if chave == "canil":
        extras[chave] = [("Adotados", numero(df["s"].eq("Adotado").sum()), "Conforme a situação do registro"), ("Castrados", numero(df["s"].eq("Castrado").sum()), "Conforme a situação do registro")]
    if chave == "notif":
        extras[chave] = [("Bairros", numero(df["b"].nunique()), "Com notificações no filtro"), ("Suspeitas de raiva", numero(df["t"].eq("Suspeita de Raiva").sum()), "Registros de suspeita, sem confirmar diagnóstico")]
    if chave == "diag":
        extras[chave] = [("Em tratamento", percentual("tr", "Em tratamento"), "Dos diagnósticos selecionados"), ("Recuperados", percentual("ev", "Recuperado"), "Conforme evolução registrada")]
    if chave == "maus":
        extras[chave] = [("Gravidade alta", percentual("gr", "Alta"), "Das ocorrências selecionadas"), ("Tipos de ocorrência", numero(df["tm"].nunique()), "Categorias presentes no filtro")]
    if chave == "obit":
        extras[chave] = [("Eutanásias", numero(df["ot"].eq("Eutanásia").sum()), "Conforme o tipo de ocorrência"), ("Óbitos", numero(df["ot"].eq("Óbito").sum()), "Conforme o tipo de ocorrência")]
    itens = [("Registros", numero(quantidade), "No período e filtros selecionados"), ("Municípios", numero(municipios), "Com registros nesta seção"), *extras[chave]]
    for coluna, (titulo, valor, detalhe) in zip(st.columns(4), itens):
        cartao(coluna, titulo, valor, detalhe)


def mostrar_grafico(fig, filtro=None, identificador=""):
    global contador_graficos
    contador_graficos += 1
    fig.update_layout(template="plotly_dark" if noturno else "plotly_white", colorway=CORES, paper_bgcolor=paleta["cartao"], plot_bgcolor=paleta["cartao"],
                      font={"family": "Segoe UI, Arial", "color": paleta["texto"]},
                      title_font={"size": 15, "color": paleta["suave"]},
                      margin={"l": 20, "r": 20, "t": 55, "b": 30}, height=330,
                      separators=",.", legend_title_text="", hoverlabel={"bgcolor": paleta["apoio"]})
    fig.update_xaxes(gridcolor=paleta["linha"])
    fig.update_yaxes(gridcolor=paleta["linha"])
    chave = f"grafico_{secao_grafico}_{identificador}_{st.session_state.get('versao_graficos', 0)}"
    extras = {}
    if filtro:
        fig.update_layout(clickmode="event+select", dragmode="select")
        extras = {"on_select": lambda: selecionar_grafico(chave, filtro), "selection_mode": "points"}
    st.plotly_chart(fig, width="stretch", key=chave, config={"displayModeBar": False, "displaylogo": False}, **extras)

TABELAS = {
    "cad": ("Animais", ["ia", "m", "e", "r", "x", "i", "d", "st", "vf", "sv"]),
    "vac": ("Vacinação", ["m", "d", "e", "n"]),
    "canil": ("Canil", ["m", "s", "d", "a"]),
    "notif": ("Notificações", ["m", "b", "t", "d"]),
    "diag": ("Diagnósticos", ["ia", "m", "do", "d", "tr", "ev"]),
    "maus": ("Maus-tratos", ["ia", "m", "tm", "d", "gr", "pv"]),
    "obit": ("Óbitos e eutanásias", ["ia", "m", "ot", "mo", "d"]),
}
NOMES = {"ia": "id_animal", "m": "município", "e": "espécie", "r": "raca",
         "x": "sexo", "i": "idade", "d": "data", "st": "status",
         "vf": "vacinas_faltantes", "sv": "situacao_vacinacao", "n": "doses",
         "s": "situação", "a": "atendimento", "b": "bairro", "t": "tipo",
         "do": "doenca", "tr": "tratamento", "ev": "evolucao", "tm": "tipo_maus_tratos",
         "gr": "gravidade", "pv": "providencias", "ot": "tipo_ocorrencia", "mo": "motivo"}


def tratar(chave, df):
    """Padroniza colunas, valida valores e rejeita importações inválidas."""
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    df = df.rename(columns={v: k for k, v in NOMES.items()})
    if df.columns.duplicated().any():
        raise ValueError("Há colunas repetidas após a padronização dos nomes.")
    faltantes = set(TABELAS[chave][1]) - set(df.columns)
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(NOMES[c] for c in sorted(faltantes)))
    if df.empty:
        raise ValueError("A tabela está vazia.")
    for c in TABELAS[chave][1]:
        if c not in ("d", "ia", "i", "n"):
            df[c] = df[c].astype("string").str.strip()
            if df[c].isna().any() or df[c].eq("").any():
                raise ValueError(f"Preencha todos os valores da coluna {NOMES[c]}.")
    def data(v):
        if isinstance(v, (float, int)) and not isinstance(v, bool):
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(v, unit="D")
        return pd.to_datetime(v, errors="coerce", dayfirst=not str(v)[:4].isdigit())
    df["d"] = df["d"].map(data)
    if df["d"].isna().any():
        raise ValueError("Há datas inválidas. Use AAAA-MM-DD ou DD/MM/AAAA.")
    df["d"] = pd.to_datetime(df["d"]).dt.normalize()
    for c in ("ia", "i", "n"):
        if c in df:
            v = pd.to_numeric(df[c], errors="coerce")
            if ((v.isna() & df[c].notna()) | (v < 0) | (v % 1 != 0) & v.notna()).any():
                raise ValueError(f"{NOMES[c]} deve conter números inteiros não negativos.")
            if c != "i" and v.isna().any():
                raise ValueError(f"Preencha {NOMES[c]}.")
            df[c] = v.astype("Int64")
    enums = {"e": ["Cão", "Gato"], "sv": ["Completa", "Incompleta"],
             "s": ["Adotado", "Castrado", "Em Tratamento", "Óbito"],
             "a": ["Clínica", "Recolhimento", "Castração"]}
    for c, valores in enums.items():
        if c in df and not df[c].isin(valores).all():
            raise ValueError(f"{NOMES[c]} aceita: {', '.join(valores)}.")
    if chave == "cad" and df["ia"].duplicated().any():
        raise ValueError("O id_animal deve ser único na tabela Animais.")
    return df


@st.cache_data
def carregar():
    dados = json.loads(Path(__file__).with_name("dados.json").read_text(encoding="utf-8"))
    return {k: tratar(k, pd.DataFrame(v)) for k, v in dados.items()}


def grafico(df, coluna, titulo, pizza=False):
    if df.empty:
        st.info(f"{titulo}: sem dados para os filtros selecionados.")
        return
    contagem = df[coluna].fillna("Não informado").value_counts().rename_axis("Categoria").reset_index(name="Registros")
    if pizza:
        fig = px.pie(contagem, names="Categoria", values="Registros", hole=.65, title=titulo, color_discrete_sequence=CORES)
        fig.update_traces(hovertemplate="%{label}<br>Registros: %{value}<extra></extra>", textinfo="percent")
    else:
        fig = px.bar(contagem.head(10), x="Registros", y="Categoria", orientation="h", title=titulo, color_discrete_sequence=CORES, custom_data=["Categoria"])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        fig.update_traces(hovertemplate="%{y}<br>Registros: %{x}<extra></extra>")
        fig.update_yaxes(title=None)
    mostrar_grafico(fig, FILTROS_GRAFICOS.get(coluna) if not pizza else None, titulo + coluna)


def evolucao(df, doses=False):
    if df.empty:
        return
    serie = df.set_index("d").resample("MS")
    serie = serie["n"].sum() if doses else serie.size()
    nome = "Doses" if doses else "Registros"
    mensal = serie.rename(nome).reset_index()
    mensal["Mês"] = mensal["d"].map(lambda d: f"{MESES[d.month-1][:3].lower()}/{d.year}")
    fig = px.area(mensal, x="Mês", y=nome, title="Evolução mensal no período selecionado", markers=True, color_discrete_sequence=CORES)
    fig.update_traces(hovertemplate="%{x}<br>" + nome + ": %{y}<extra></extra>")
    mostrar_grafico(fig, identificador="evolucao")


if "dados" not in st.session_state:
    st.session_state.dados = carregar()
dados = st.session_state.dados
cabecalho = st.empty()
if pagina == "Gerenciar dados":
    cabecalho.markdown('<div class="hero"><h1>Gerenciar dados do painel</h1><p>Importação, exportação e restauração das tabelas</p></div>', unsafe_allow_html=True)

def gerenciar_dados():
    titulo_secao("Preparar e importar", "Siga as etapas abaixo para atualizar uma tabela. Os arquivos originais são preservados.")
    preparar, importar = st.columns([1, 1.35], gap="large")
    with preparar:
        st.markdown("### 1. Escolha a tabela")
        destino = st.selectbox("Tabela", list(TABELAS), format_func=lambda k: TABELAS[k][0])
        csv = dados[destino].rename(columns=NOMES).to_csv(index=False, sep=";", date_format="%Y-%m-%d").encode("utf-8-sig")
        st.download_button("Baixar CSV da tabela", csv, f"{destino}.csv", "text/csv")
        with st.expander("Consultar colunas e exemplos"):
            st.dataframe(dados[destino].head(5).rename(columns=NOMES), hide_index=True, width="stretch")
    with importar:
        st.markdown("### 2. Importe a planilha")
        st.info("A tabela escolhida será substituída por completo. As outras tabelas serão preservadas.")
        with st.form("importacao"):
            arquivo = st.file_uploader("Selecione uma planilha CSV ou Excel", type=["csv", "xlsx"], help="Use o botão de seleção abaixo para escolher o arquivo no computador.")
            aplicar = st.form_submit_button("Validar e substituir tabela")
    if aplicar and arquivo is None:
        st.warning("Selecione uma planilha antes de importar.")
    if aplicar and arquivo is not None:
        try:
            if arquivo.name.lower().endswith("xlsx"):
                novo = pd.read_excel(arquivo)
            else:
                bruto = arquivo.getvalue()
                try:
                    texto = bruto.decode("utf-8-sig")
                except UnicodeDecodeError:
                    texto = bruto.decode("cp1252")
                novo = pd.read_csv(io.StringIO(texto), sep=None, engine="python")
            novo = tratar(destino, novo)
            proximos = {**dados, destino: novo}
            ids = set(proximos["cad"]["ia"])
            for k in ("diag", "maus", "obit"):
                if not proximos[k]["ia"].isin(ids).all():
                    raise ValueError(f"{TABELAS[k][0]} contém id_animal sem cadastro na tabela Animais.")
            st.session_state.dados = proximos
            limpar_filtros()
            st.session_state["mensagem_importacao"] = f"Importação concluída: {len(novo)} registros em {TABELAS[destino][0]}."
            st.rerun()
        except (ValueError, TypeError, OverflowError, OSError, KeyError) as erro:
            st.error(f"Importação rejeitada: {erro}")
    st.caption("Importações ficam nesta sessão. Baixe o CSV para guardar as alterações. Os dados originais permanecem em dados.json.")
    with st.expander("Restaurar dados originais"):
        st.caption("Esta ação descarta as importações de todas as tabelas nesta sessão.")
        confirmar = st.checkbox("Quero descartar as importações desta sessão")
        if st.button("Restaurar todas as tabelas originais", disabled=not confirmar):
            st.session_state.dados = carregar()
            limpar_filtros()
            st.rerun()


if pagina == "Gerenciar dados":
    for chave in list(st.session_state):
        if chave.startswith("f_"):
            st.session_state[chave] = st.session_state[chave]
    if "mensagem_importacao" in st.session_state:
        st.success(st.session_state.pop("mensagem_importacao"))
    gerenciar_dados()
    st.stop()

with st.container(key="filtros_compactos"):
    selecoes = {}
    posicao = [0]
    colunas_filtro = st.columns(8)
    def filtro(nome, valores):
        if posicao[0] == 8:
            colunas_filtro[:] = st.columns(8)
        coluna = colunas_filtro[posicao[0] % 8]
        posicao[0] += 1
        opcoes = sorted(pd.Series(valores).dropna().unique().tolist())
        chave = "f_" + nome
        return coluna.multiselect(nome, ["Selecionar todos", *opcoes], key=chave,
                                  placeholder="Todos", select_all=False,
                                  on_change=selecionar_todos, args=(chave, opcoes),
                                  format_func=lambda v: MESES[int(v)-1] if nome == "Mês" and v != "Selecionar todos" else str(v))
    datas = pd.concat([v["d"] for v in dados.values()])
    anos = filtro("Ano", datas.dt.year)
    meses = filtro("Mês", datas.dt.month)
    municipios = filtro("Município", pd.concat([v["m"] for v in dados.values()]))
    selecoes["e"] = filtro("Espécie", dados["cad"]["e"])
    especificos = {"canil": [("s", "Situação no canil"), ("a", "Atendimento")],
                   "notif": [("t", "Tipo de notificação"), ("b", "Bairro")],
                   "diag": [("do", "Doença")], "maus": [("tm", "Tipo de maus-tratos"), ("gr", "Gravidade")],
                   "obit": [("ot", "Óbito / Eutanásia")]}
    locais = {}
    for k, c, label in [("notif", "t", "Tipo de notificação"), ("canil", "s", "Situação no canil"), ("notif", "b", "Bairro"), ("canil", "a", "Atendimento")]:
        locais[k, c] = filtro(label, dados[k][c])
    for c, label in [("r", "Raça"), ("x", "Sexo")]:
        selecoes[c] = filtro(label, dados["cad"][c])
    for k in ("diag", "maus", "obit"):
        for c, label in especificos[k]:
            locais[k, c] = filtro(label, dados[k][c])
    with colunas_filtro[6]:
        st.markdown('<div class="espaco-botao"></div>', unsafe_allow_html=True)
        st.button("Limpar filtros", on_click=limpar_filtros, width="stretch")
    st.caption("Seleção múltipla. Espécie, raça e sexo filtram animais e registros vinculados; espécie também filtra vacinação. Os demais filtros se aplicam à própria seção. Clique nas barras para filtrar; Shift soma seleções.")

ativos = []
for chave, valores in st.session_state.items():
    if chave.startswith("f_") and valores:
        texto = [MESES[int(v)-1] if chave == "f_Mês" else str(v) for v in valores]
        ativos.append(chave[2:] + ": " + ", ".join(texto))
if ativos:
    st.caption(" • ".join(ativos))
if pagina != "Gerenciar dados":
    periodo = f"{datas.min():%d/%m/%Y} a {datas.max():%d/%m/%Y}"
    subtitulo = " · ".join([", ".join(municipios) if municipios else "Todos os municípios", ", ".join(selecoes["e"]) if selecoes["e"] else "Cães e gatos", periodo])
    cabecalho.markdown(f'<div class="hero"><h1>Painel de Zoonoses e Controle Animal</h1><p>{escape(subtitulo)}</p></div>', unsafe_allow_html=True)

animais = dados["cad"]
mascara = pd.Series(True, index=animais.index)
for c, valores in selecoes.items():
    if valores:
        mascara &= animais[c].isin(valores)
ids = set(animais.loc[mascara, "ia"])
filtrados = {}
for k, original in dados.items():
    df = original.copy()
    if anos:
        df = df[df["d"].dt.year.isin(anos)]
    if meses:
        df = df[df["d"].dt.month.isin(meses)]
    if municipios:
        df = df[df["m"].isin(municipios)]
    if k == "cad" or k in ("diag", "maus", "obit"):
        df = df[df["ia"].isin(ids)]
    if k == "vac" and selecoes["e"]:
        df = df[df["e"].isin(selecoes["e"])]
    for c, _ in especificos.get(k, []):
        if locais[k, c]:
            df = df[df[c].isin(locais[k, c])]
    filtrados[k] = df

a, v, c, n = [filtrados[k] for k in ("cad", "vac", "canil", "notif")]
completos = a["sv"].eq("Completa").sum()
cols = st.columns(6) if pagina == "Visão geral" else []
metricas = [("Animais", len(a)), ("Doses", int(v["n"].sum())),
            ("Vacinação completa", f"{completos / len(a):.1%}".replace(".", ",") if len(a) else "Sem dados"),
            ("Registros no canil", len(c)), ("Castrados no canil", int(c["s"].eq("Castrado").sum())), ("Notificações", len(n))]
icones = ["♡", "♧", "◇", "⌂", "✂", "♧"]
detalhes = [f'{int(a["e"].eq("Cão").sum()):,} cães · {int(a["e"].eq("Gato").sum()):,} gatos'.replace(",", "."),
            f"{len(v)} aplicações · doses registradas", f"{int(completos):,} de {len(a):,} vacinados".replace(",", "."),
            f'{int(c["s"].eq("Adotado").sum())} adotados', "Conforme situação no canil", f'{int(n["t"].eq("Suspeita de Raiva").sum())} suspeitas de raiva']
for col, (label, valor), icone, detalhe in zip(cols, metricas, icones, detalhes):
    valor = f"{valor:,}".replace(",", ".") if isinstance(valor, int) else valor
    col.markdown(f'<div class="indicador"><div class="icone-indicador">{icone}</div><div class="rotulo-indicador">{escape(label)}</div><div class="valor-indicador">{escape(str(valor))}</div><div class="detalhe-indicador">{escape(detalhe)}</div></div>', unsafe_allow_html=True)

if pagina == "Visão geral":
    titulo_secao("Destaques do período", "Uma leitura rápida dos registros que correspondem aos filtros selecionados.")
    destaques = st.columns(3)
    with destaques[0]:
        with st.container(border=True):
            st.markdown("**Maior volume de notificações**")
            if n.empty:
                st.write("Sem notificações no filtro")
            else:
                contagem = n["m"].value_counts()
                st.write(str(contagem.index[0]))
                st.caption(f"{int(contagem.iloc[0])} registros • {contagem.iloc[0]/len(n):.1%} do total".replace(".", ","))
    with destaques[1]:
        with st.container(border=True):
            st.markdown("**Situação da vacinação**")
            pendentes = len(a) - int(completos)
            st.write(f"{pendentes:,} cadastros incompletos".replace(",", ".") if len(a) else "Sem cadastros no filtro")
            st.caption("Conforme a situação vacinal registrada nos cadastros")
    with destaques[2]:
        with st.container(border=True):
            st.markdown("**Adoções no canil**")
            adotados = int(c["s"].eq("Adotado").sum())
            st.write(f"{adotados} registros de adoção")
            st.caption(f"{adotados/len(c):.1%} dos registros do canil".replace(".", ",") if len(c) else "Sem registros no filtro")
    titulo_secao("Distribuição dos registros", "Compare espécies, municípios, notificações e situação no canil.")
    esquerda, direita = st.columns(2)
    with esquerda:
        grafico(a, "e", "Animais por espécie", pizza=True)
    with direita:
        grafico(n, "t", "Tipos de notificação", pizza=True)
    esquerda, direita = st.columns(2)
    with esquerda:
        grafico(a, "m", "Animais por município")
    with direita:
        grafico(c, "s", "Situação dos registros no canil", pizza=True)
    titulo_secao("Resumo por município", "Contagens de cada seção e total de doses aplicadas.")
    resumo = pd.DataFrame(index=sorted(pd.concat([v["m"] for v in dados.values()]).unique()))
    for k, df in filtrados.items():
        resumo[TABELAS[k][0]] = df.groupby("m").size()
    resumo["Doses"] = v.groupby("m")["n"].sum()
    resumo = resumo.fillna(0).astype(int)
    if municipios:
        resumo = resumo.loc[resumo.index.isin(municipios)]
    resumo.index.name = "Município"
    st.dataframe(resumo, width="stretch")

CAMPOS = {"cad": [("e", "Espécies"), ("x", "Sexo"), ("r", "Raças"), ("st", "Situação cadastral"), ("sv", "Situação vacinal")],
          "vac": [("e", "Aplicações por espécie")], "canil": [("s", "Situação"), ("a", "Atendimentos")],
          "notif": [("t", "Tipos de ocorrência"), ("b", "Bairros")],
          "diag": [("do", "Doenças"), ("tr", "Tratamento"), ("ev", "Evolução clínica")],
          "maus": [("tm", "Tipos de maus-tratos"), ("gr", "Gravidade"), ("pv", "Providências")],
          "obit": [("ot", "Tipos de ocorrência"), ("mo", "Motivos")]}
for k in TABELAS:
    if pagina == TABELAS[k][0]:
        secao_grafico = k
        df = filtrados[k]
        titulo_secao(TABELAS[k][0], "Indicadores desta seção • Todos os valores respeitam os filtros acima.")
        indicadores_secao(k, df)
        if df.empty:
            st.info("Nenhum registro corresponde a esta combinação de filtros. Ajuste as seleções ou use Limpar filtros.")
        titulo_secao("Perfil e distribuição", "Passe o mouse para consultar valores. Nos gráficos de barras, clique para filtrar.")
        campos = [*CAMPOS[k], ("m", "Registros por município")]
        for j, (campo, titulo) in enumerate(campos):
            if j % 2 == 0:
                esquerda, direita = st.columns(2)
            with (esquerda if j % 2 == 0 else direita):
                grafico(df, campo, titulo, pizza=campo in ("e", "x", "sv", "gr", "ot", "s"))
        if len(campos) % 2:
            with direita:
                evolucao(df, doses=k == "vac")
        else:
            titulo_secao("Evolução no tempo", "Totais mensais dentro do período selecionado.")
            evolucao(df, doses=k == "vac")
        titulo_secao("Consultar e exportar", "Pesquise os registros e baixe o resultado da consulta em CSV.")
        with st.container(border=True, key="consulta_registros"):
            pesquisa, ordenacao = st.columns([3, 1])
            busca = pesquisa.text_input("Pesquisar registros", key=f"busca_{k}", placeholder="Município, categoria ou outro termo")
            ordem = ordenacao.selectbox("Ordenar por data", ["Mais recentes", "Mais antigos"], key=f"ordem_{k}")
        df = df.sort_values("d", ascending=ordem == "Mais antigos")
        exibicao = df.rename(columns=ROTULOS).copy()
        exibicao["Data"] = exibicao["Data"].dt.strftime("%d/%m/%Y")
        if busca:
            exibicao = exibicao[exibicao.astype(str).apply(lambda col: col.str.contains(busca, case=False, regex=False)).any(axis=1)]
        st.caption(f"{numero(len(exibicao))} registros encontrados • {numero(len(df))} registros antes da pesquisa")
        st.dataframe(exibicao, width="stretch", hide_index=True, height=380)
        st.download_button("Baixar resultado da consulta", df.loc[exibicao.index].rename(columns=NOMES).to_csv(index=False, sep=";", date_format="%Y-%m-%d").encode("utf-8-sig"), f"{k}_filtrado.csv", "text/csv", key=f"exportar_{k}")

