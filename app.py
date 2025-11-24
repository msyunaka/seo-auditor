import streamlit as st
from googleapiclient.discovery import build
import requests
import pandas as pd
import time

# --- Configuração Visual ---
st.set_page_config(page_title="SEO Link Auditor", layout="wide", page_icon="🕵️‍♂️")

st.title("🕵️‍♂️ Auditor SEO: Controle Total")
st.markdown("Auditoria de backlinks com controle total sobre o comando enviado ao Google.")

# --- Credenciais ---
if 'GOOGLE_API_KEY' in st.secrets and 'SEARCH_ENGINE_ID' in st.secrets:
    api_key = st.secrets['GOOGLE_API_KEY']
    cse_id = st.secrets['SEARCH_ENGINE_ID']
    credentials_ok = True
else:
    st.warning("⚠️ Configure suas chaves no secrets.toml")
    credentials_ok = False

# --- Core do Sistema ---

def google_search(query, api_key, cse_id, num_results):
    results = []
    service = build("customsearch", "v1", developerKey=api_key)
    
    status_box = st.status(f"Enviando comando: '{query}'", expanded=True)
    
    # Paginação
    for start_index in range(1, num_results + 1, 10):
        try:
            status_box.write(f"📡 Solicitando lote {start_index} a {start_index+9}...")
            time.sleep(0.3)
            
            res = service.cse().list(
                q=query,
                cx=cse_id,
                start=start_index,
                num=10,
                filter='0' # Desliga filtro de duplicados (CRUCIAL)
            ).execute()
            
            if 'items' in res:
                for item in res['items']:
                    results.append({
                        'Título': item.get('title'),
                        'Link de Origem': item.get('link'),
                        'Trecho': item.get('snippet'),
                        'Status': 'Pendente',
                        'Verificado': False
                    })
            else:
                break
        except Exception as e:
            # st.error(f"Erro API: {e}") # Debug se necessário
            break
            
        if len(results) >= num_results:
            break
    
    status_box.update(label=f"✅ Finalizado. {len(results)} resultados recuperados via API.", state="complete", expanded=False)
    return pd.DataFrame(results)

def check_status_code(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        return str(response.status_code)
    except:
        return "Erro"

# --- Interface de Controle ---

col1, col2 = st.columns([1, 1])

with col1:
    # Input simples para gerar a sugestão
    target_site = st.text_input("Domínio Base (Opcional):", placeholder="zildasimao.com.br")
    if target_site:
        clean = target_site.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        # Sugestão padrão baseada no que você pediu
        default_query = f"link:{clean} -site:{clean}"
    else:
        default_query = ""

with col2:
    # Slider de quantidade
    qtd_busca = st.slider("Meta de Resultados:", 10, 100, 50, 10)

st.divider()

# --- O PULO DO GATO: CAMPO TOTALMENTE EDITÁVEL ---
st.subheader("📢 Comando Exato para o Google")
st.caption("Abaixo está o texto exato que será enviado. Você pode editar para ficar IDÊNTICO à sua busca no navegador.")

# O usuário pode mudar isso manualmente se quiser
final_query = st.text_input("Query:", value=default_query, placeholder="link:site.com.br -site:site.com.br")

btn_search = st.button("🚀 EXECUTAR COMANDO EXATO", type="primary", use_container_width=True)

# --- Execução ---

if btn_search and credentials_ok:
    if not final_query:
        st.warning("O campo de comando (Query) está vazio.")
    else:
        # Envia a string exata, sem "interpretações" do Python
        df = google_search(final_query, api_key, cse_id, num_results=qtd_busca)
        
        if not df.empty:
            st.session_state['df_results'] = df
            st.rerun()
        else:
            st.error("A API do Google retornou 0 resultados para este comando exato.")
            st.info("💡 Análise: Se no navegador funciona e aqui não, é uma limitação da 'Custom Search API' em relação ao operador 'link:'. Tente usar o comando 'site.com.br -site:site.com.br' (sem o 'link:') para ver se a API libera mais dados.")

# --- Tabela ---

if 'df_results' in st.session_state:
    df = st.session_state['df_results']
    st.divider()
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Verificado": st.column_config.CheckboxColumn("Sel.", default=True, width="small"),
            "Link de Origem": st.column_config.LinkColumn("URL Encontrada", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        disabled=["Título", "Link de Origem", "Trecho", "Status"],
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    if st.button("⚡ Testar Status"):
        bar = st.progress(0)
        to_check = edited_df[edited_df['Verificado']].index
        total = len(to_check)
        
        for i, idx in enumerate(to_check):
            url = edited_df.at[idx, 'Link de Origem']
            code = check_status_code(url)
            
            if code == '200': d = "🟢 200"
            elif code == '404': d = "🔴 404"
            else: d = f"🟠 {code}"
            
            st.session_state['df_results'].at[idx, 'Status'] = d
            bar.progress((i + 1) / total)
            
        st.rerun()
