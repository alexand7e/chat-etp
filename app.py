import streamlit as st
import google.generativeai as genai
import os
from docx import Document

# Função para configurar o modelo Gemini com cache
@st.cache_resource
def setup_gemini_model(api_key, system_instruction):
    try:
        genai.configure(api_key=api_key)

        # Configurações de geração
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        # Modelo com instruções de sistema
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
            system_instruction=system_instruction
        )

        return model
    except Exception as e:
        st.error(f"Erro ao configurar o modelo: {e}")
        return None

# Função para carregar instruções do sistema
def load_system_instruction(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Arquivo '{filepath}' não encontrado.")
        return ""
    except Exception as e:
        st.error(f"Erro ao carregar instruções: {e}")
        return ""

import os
import streamlit as st
from docx import Document

def main():
    st.title("Relatório ETP | Governo do Estado do Piauí")

    # Input para a chave API
    api_key = st.sidebar.text_input("Digite sua Chave API do Gemini", type="password")

    # Carregar instruções do sistema
    system_instruction = load_system_instruction(os.path.join(os.path.dirname(__file__), "comandos.txt"))

    # Verifica se a chave API foi fornecida
    if api_key and system_instruction:
        # Configura o modelo Gemini usando cache
        model = setup_gemini_model(api_key, system_instruction)

        if model:
            # Barra lateral para navegação de chats
            st.sidebar.header("Histórico de Chats")
            if 'chat_sessions' not in st.session_state:
                st.session_state.chat_sessions = {}
            if 'active_chat' not in st.session_state:
                st.session_state.active_chat = "Novo Chat"
            if 'report_generated' not in st.session_state:
                st.session_state.report_generated = False

            # Exibe opções de chat na barra lateral
            chat_names = list(st.session_state.chat_sessions.keys()) + ["Novo Chat"]
            selected_chat = st.sidebar.selectbox("Selecione o Chat", chat_names)

            if st.sidebar.button("Criar Novo Chat"):
                chat_name = f"Chat {len(st.session_state.chat_sessions) + 1}"
                st.session_state.chat_sessions[chat_name] = model.start_chat(history=[])
                st.session_state.active_chat = chat_name
                st.session_state.report_generated = False

            if selected_chat != st.session_state.active_chat:
                st.session_state.active_chat = selected_chat

            active_chat = st.session_state.active_chat

            if active_chat not in st.session_state.chat_sessions:
                st.session_state.chat_sessions[active_chat] = model.start_chat(history=[])

            chat_session = st.session_state.chat_sessions[active_chat]

            # Formulário retrátil
            with st.expander("Formulário para Relatório", expanded=not st.session_state.report_generated):
                with st.form("formulario_relatorio"):
                    nome_objeto = st.text_input("Nome do Objeto")
                    descricao_itens = st.text_area("Descrição dos Itens")
                    quantitativo_itens = st.number_input("Quantitativo dos Itens", min_value=0)
                    unidade_medida = st.text_input("Unidade de Medida")
                    setor_requisitante = st.text_input("Setor Requisitante")
                    numero_processo = st.text_input("Número do Processo")
                    informacoes_adicionais = st.text_area("Informações Adicionais")
                    submit_button = st.form_submit_button("Gerar Relatório")

                if submit_button:
                    # Primeira mensagem para o modelo
                    initial_message = f"""
                    Nome do Objeto: {nome_objeto}
                    Descrição dos Itens: {descricao_itens}
                    Quantitativo dos Itens: {quantitativo_itens}
                    Unidade de Medida: {unidade_medida}
                    Setor Requisitante: {setor_requisitante}
                    Número do Processo: {numero_processo}
                    Informações Adicionais: {informacoes_adicionais}
                    """
                    try:
                        with st.spinner("Gerando a primeira versão do relatório..."):
                            response = chat_session.send_message(initial_message)
                            st.session_state.report_generated = True

                        # Exibe a resposta do modelo
                        st.success("Relatório gerado com sucesso!")
                        st.chat_message("assistant").write(response.text)

                        # Salvar em Word
                        doc = Document()
                        doc.add_heading(f"Chat: {active_chat}", level=1)
                        doc.add_paragraph(response.text)
                        doc_path = f"{active_chat}.docx"
                        doc.save(doc_path)

                        with open(doc_path, "rb") as file:
                            st.download_button(
                                label="Baixar Documento Word",
                                data=file,
                                file_name=os.path.join(os.path.dirname(__file__), "relatórios", f"{active_chat}.docx"),
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                    except Exception as e:
                        st.error(f"Erro ao gerar o relatório: {e}")

            # Habilita o chat somente após o relatório inicial
            if st.session_state.report_generated:
                st.header(f"Chat Ativo: {active_chat}")
                for message in chat_session.history:
                    if message.role == "user":
                        st.chat_message("user").write(message.parts[0].text)
                    else:
                        st.chat_message("assistant").write(message.parts[0].text)

                # Input de mensagem do usuário
                if prompt := st.chat_input("Digite sua mensagem"):
                    st.chat_message("user").write(prompt)
                    try:
                        with st.spinner("Gerando resposta..."):
                            response = chat_session.send_message(prompt)

                        st.chat_message("assistant").write(response.text)

                    except Exception as e:
                        st.error(f"Erro ao enviar mensagem: {e}")
    else:
        st.warning("Por favor, insira sua chave API do Gemini e certifique-se de que o arquivo './comandos.txt' está disponível.")


# Executa a aplicação
if __name__ == "__main__":
    main()
