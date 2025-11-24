import streamlit as st
from googleapiclient.discovery import build
import requests
import pandas as pd
import time

# --- Configuração da Página ---
st.set_page_config(page_title="SEO Link Auditor", layout="wide")

st.title("🕵️ Agência SEO - Auditor de Referências")

# --- Gerenciamento de Credenciais (Automático) ---
# Tenta pegar dos 'Segredos' do sistema (Nuvem)
if 'GOOGLE_API_KEY' in st.secrets and 'SEARCH_ENGINE_ID' in st.secrets:
    api_key = st.secrets['GOOGLE_API_KEY']
    cse_id = st.secrets['SEARCH_ENGINE_ID']
    credentials_ok = True
    st.success("✅ Conexão com Google API: Ativa (Credenciais Internas)")
else:
    # Se não achar (uso local sem config), pede na tela
    st.warning("⚠️ Credenciais não configuradas no servidor. Digite abaixo:")
    with st.sidebar:
        api_key = st.text_input("Google API Key", type="password")
        cse_id = st.text_input("Search Engine ID (CX)")
    credentials_ok = bool(api_key and cse_id)

# --- Funções do Sistema ---

def google_search(query, api_key, cse_id, num_results=20):
    """Busca no Google usando a API oficial."""
    results = []
    try:
        service = build("customsearch", "v1", developerKey=api_key)
        pages_to_fetch = (num_results // 10) + 1
        
        with st.spinner(f"Minerando o Google..."):
            for i in range(pages_to_fetch):
                start_index = (i * 10) + 1
                res = service.cse().list(
                    q=query, cx=cse_id, start=start_index, num=10
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
                time.sleep(0.2)
                if len(results) >= num_results:
                    break
    except Exception as e:
        st.error(f"Erro na API do Google: {e}")
        return pd.DataFrame()
                
    return pd.DataFrame(results)

def check_status_code(url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; SEOAuditBot/1.0)'}
    try:
        response = requests.get(url, headers=headers, timeout=8)
        return str(response.status_code)
    except:
        return "Erro"

# --- Interface Principal ---

col_input, col_btn = st.columns([3, 1])
with col_input:
    target_site = st.text_input("Domínio do Cliente (ex: site.com.br):")
with col_btn:
    st.write("") # Espaçamento
    st.write("")
    btn_search = st.button("🔍 Buscar Referências", type="primary")

if btn_search and credentials_ok:
    if not target_site:
        st.warning("Por favor, digite um domínio.")
    else:
        # Query: busca o termo, exclui o site do cliente
        query = f'"{target_site}" -site:{target_site}'
        df = google_search(query, api_key, cse_id, num_results=40) # Padrão 40 para ser rápido
        
        if not df.empty:
            st.session_state['df_results'] = df
        else:
            st.info("Nenhum resultado encontrado para esta busca.")

# --- Tabela e Ações ---

if 'df_results' in st.session_state:
    df = st.session_state['df_results']
    st.markdown("### Resultados Encontrados")
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Verificado": st.column_config.CheckboxColumn("Selecionar", default=True),
            "Link de Origem": st.column_config.LinkColumn("Link")
        },
        disabled=["Título", "Link de Origem", "Trecho", "Status"],
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("⚡ Verificar Status dos Links Selecionados"):
        progress_bar = st.progress(0)
        
        # Índices marcados como True
        to_check = edited_df[edited_df['Verificado']].index
        total = len(to_check)
        
        for i, idx in enumerate(to_check):
            url = edited_df.at[idx, 'Link de Origem']
            code = check_status_code(url)
            
            # Atualiza visualmente (Emojis)
            if code == '200': code_display = "🟢 200 OK"
            elif code == '404': code_display = "🔴 404 (Quebrado)"
            else: code_display = f"🟠 {code}"
            
            st.session_state['df_results'].at[idx, 'Status'] = code_display
            progress_bar.progress((i + 1) / total)
            
        st.rerun()