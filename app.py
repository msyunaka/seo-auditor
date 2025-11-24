import streamlit as st
from googleapiclient.discovery import build
import requests
import pandas as pd
import time

# --- Configuração da Página ---
st.set_page_config(page_title="SEO Link Auditor", layout="wide", page_icon="🕵️")

st.title("🕵️ Agência SEO - Auditor de Backlinks")
st.markdown("Busca referências exatas ao domínio, verifica status e desativa filtros de duplicidade do Google.")

# --- Gerenciamento de Credenciais ---
if 'GOOGLE_API_KEY' in st.secrets and 'SEARCH_ENGINE_ID' in st.secrets:
    api_key = st.secrets['GOOGLE_API_KEY']
    cse_id = st.secrets['SEARCH_ENGINE_ID']
    credentials_ok = True
    st.success("✅ Conexão API: Ativa (Nuvem)")
else:
    st.warning("⚠️ Credenciais não encontradas. Configure os Secrets ou digite ao lado.")
    with st.sidebar:
        api_key = st.text_input("Google API Key", type="password")
        cse_id = st.text_input("Search Engine ID (CX)")
    credentials_ok = bool(api_key and cse_id)

# --- Funções do Sistema ---

def google_search(query, api_key, cse_id, num_results=50):
    """
    Busca no Google usando a API oficial.
    MODIFICAÇÃO: filter='0' desliga o filtro de duplicados para trazer mais resultados.
    """
    results = []
    service = build("customsearch", "v1", developerKey=api_key)
    
    # O Google retorna max 10 por requisição. Precisamos paginar.
    # Ex: Para 50 resultados, loop roda 5 vezes.
    
    with st.spinner(f"Minerando o Google sem filtros..."):
        # Começa em 1, pula de 10 em 10 (1, 11, 21, 31...)
        for start_index in range(1, num_results + 1, 10):
            try:
                # Pausa para não bloquear a API
                time.sleep(0.2)
                
                res = service.cse().list(
                    q=query,
                    cx=cse_id,
                    start=start_index,
                    num=10,        # Máximo permitido por vez
                    filter='0'     # <--- O SEGREDO: Traz resultados que o Google ocultaria
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
                    # Se não tem 'items', acabaram os resultados
                    break
                    
            except Exception as e:
                # Se der erro (ex: limite de profundidade), para o loop mas não trava o app
                # st.error(f"Aviso técnico: {e}") 
                break
            
            # Se já pegou o suficiente, para
            if len(results) >= num_results:
                break
                
    return pd.DataFrame(results)

def check_status_code(url):
    """Verifica se a página está online (200) ou erro (404)."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return str(response.status_code)
    except:
        return "Erro"

# --- Interface Principal ---

col1, col2 = st.columns([3, 1])
with col1:
    target_site = st.text_input("Digite o domínio do cliente:", placeholder="ex: zildasimao.com.br")
with col2:
    st.write("")
    st.write("")
    btn_search = st.button("🔍 Buscar Agora", type="primary", use_container_width=True)

# --- Lógica de Busca ---

if btn_search and credentials_ok:
    if not target_site:
        st.warning("Por favor, digite o site.")
    else:
        # 1. Limpeza do domínio (tira https, www, barras)
        clean_site = target_site.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        
        # 2. Query Exata: "site" -site:site
        query = f'"{clean_site}" -site:{clean_site}'
        
        st.info(f"Buscando referências para: {clean_site}")
        
        # 3. Chama a função (agora buscando até 60 resultados para garantir)
        df = google_search(query, api_key, cse_id, num_results=60)
        
        if not df.empty:
            st.session_state['df_results'] = df
            st.rerun()
        else:
            st.warning("O Google não encontrou resultados com esses parâmetros.")
            st.markdown(f"**Dica:** Verifique se o site tem backlinks indexados buscando manualmente por `{query}` no Google.")

# --- Tabela de Resultados ---

if 'df_results' in st.session_state:
    df = st.session_state['df_results']
    
    st.divider()
    st.subheader(f"Encontrados: {len(df)} referências")
    
    # Tabela Editável
    edited_df = st.data_editor(
        df,
        column_config={
            "Verificado": st.column_config.CheckboxColumn("Selecionar", default=True, width="small"),
            "Link de Origem": st.column_config.LinkColumn("Link Encontrado"),
            "Status": st.column_config.TextColumn("Status HTTP", width="medium"),
        },
        disabled=["Título", "Link de Origem", "Trecho", "Status"],
        use_container_width=True,
        hide_index=True
    )
    
    # Botão de Verificar Status
    if st.button("⚡ Testar Status dos Selecionados"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Pega indices marcados
        to_check = edited_df[edited_df['Verificado']].index
        total = len(to_check)
        
        if total == 0:
            st.warning("Selecione pelo menos um link na tabela.")
        else:
            for i, idx in enumerate(to_check):
                url = edited_df.at[idx, 'Link de Origem']
                status_text.text(f"Testando: {url}...")
                
                code = check_status_code(url)
                
                # Formatação Visual do Status
                if code == '200': 
                    display = "🟢 200 OK"
                elif code == '404': 
                    display = "🔴 404 Off"
                elif code == 'Erro':
                    display = "⚠️ Falha Conexão"
                else: 
                    display = f"🟠 {code}"
                
                # Salva no estado
                st.session_state['df_results'].at[idx, 'Status'] = display
                
                # Atualiza barra
                progress_bar.progress((i + 1) / total)
            
            status_text.text("Verificação Completa!")
            st.rerun()
