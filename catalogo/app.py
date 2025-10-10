# app.py

from flask import Flask, render_template, request, redirect, url_for, session
import json
# Importação de Werkzeug (o framework por baixo do Flask) não é mais estritamente necessária aqui, 
# mas mantivemos o código limpo. O erro vinha de rotas mal-declaradas.

app = Flask(__name__)
# CRUCIAL: A chave secreta protege as sessões (login) do Flask.
app.secret_key = 'uma-chave-secreta-muito-forte-aqui' 

# Credenciais de acesso
USUARIO_CORRETO = "resort"
SENHA_CORRETA = "resort0809" 

# --- Funções Auxiliares de Dados ---

def carregar_cardapio_completo():
    """Lê todas as categorias do arquivo JSON."""
    try:
        with open('dados.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('cardapio', {})
    except (FileNotFoundError, json.JSONDecodeError):
        # Retorna um cardápio vazio se o arquivo não existir ou estiver inválido
        return {}


def salvar_catalogo(novas_categorias):
    """Sobrescreve o JSON com o novo dicionário de categorias."""
    data = {"cardapio": novas_categorias}
    with open('dados.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- ROTA PRINCIPAL (CATÁLOGO) ---

@app.route('/')
def index():
    cardapio_completo = carregar_cardapio_completo()
    return render_template('index.html', cardapio=cardapio_completo) 


# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == USUARIO_CORRETO and password == SENHA_CORRETA:
            session['logged_in'] = True
            return redirect(url_for('configuracoes'))
        else:
            return render_template('login.html', error='Usuário ou senha inválidos.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


# --- ROTAS DE AÇÃO PARA MOVER ITENS ---

@app.route('/move_category_action/<category_key>/<direction>')
def move_category_action(category_key, direction):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cardapio_atual = carregar_cardapio_completo()
    chaves = list(cardapio_atual.keys())
    
    try:
        index = chaves.index(category_key)
    except ValueError:
        return redirect(url_for('configuracoes')) 

    if direction == 'up' and index > 0:
        chaves[index], chaves[index - 1] = chaves[index - 1], chaves[index]
    elif direction == 'down' and index < len(chaves) - 1:
        chaves[index], chaves[index + 1] = chaves[index + 1], chaves[index]

    novo_cardapio_ordenado = {chave: cardapio_atual[chave] for chave in chaves}
    salvar_catalogo(novo_cardapio_ordenado)
    
    return redirect(url_for('configuracoes'))


@app.route('/move_item_action/<category_key>/<int:item_index>/<direction>')
def move_item_action(category_key, item_index, direction):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cardapio_atual = carregar_cardapio_completo()

    if category_key in cardapio_atual:
        lista_produtos = cardapio_atual[category_key]
        
        if 0 <= item_index < len(lista_produtos):
            if direction == 'up' and item_index > 0:
                lista_produtos[item_index], lista_produtos[item_index - 1] = lista_produtos[item_index - 1], lista_produtos[item_index]
                salvar_catalogo(cardapio_atual)
            elif direction == 'down' and item_index < len(lista_produtos) - 1:
                lista_produtos[item_index], lista_produtos[item_index + 1] = lista_produtos[item_index + 1], lista_produtos[item_index]
                salvar_catalogo(cardapio_atual)

    return redirect(url_for('configuracoes'))


# --- ROTAS DE EXCLUSÃO (DELETE) ---
# ESTAS ROTAS ESTÃO NO NÍVEL SUPERIOR DO ARQUIVO, ONDE DEVEM ESTAR.

@app.route('/delete_category/<category_key>')
def delete_category(category_key):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cardapio_atual = carregar_cardapio_completo()
    
    if category_key in cardapio_atual:
        del cardapio_atual[category_key]
        salvar_catalogo(cardapio_atual)

    # Redireciona com flag para dar alerta de sucesso
    return redirect(url_for('configuracoes', status='deleted'))


@app.route('/delete_item/<category_key>/<int:item_index>')
def delete_item(category_key, item_index):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cardapio_atual = carregar_cardapio_completo()
    
    if category_key in cardapio_atual:
        lista_produtos = cardapio_atual[category_key]
        
        if 0 <= item_index < len(lista_produtos):
            del lista_produtos[item_index]
            salvar_catalogo(cardapio_atual)

    # Redireciona com flag para dar alerta de sucesso
    return redirect(url_for('configuracoes', status='deleted'))


# --- ROTA DE CONFIGURAÇÕES (RECEBE POSTS DE EDIÇÃO/ADIÇÃO) ---

@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    cardapio_atual = carregar_cardapio_completo()

    if request.method == 'POST':
        action = request.form.get('action') 

        if action == 'add_category':
            # --- Adicionar Categoria ---
            new_name = request.form['new_category_name'].strip()
            # Gera a chave amigável
            category_key = new_name.lower().replace(' ', '_').replace('ç', 'c').replace('ã', 'a').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            
            if category_key and category_key not in cardapio_atual:
                cardapio_atual[category_key] = []
                salvar_catalogo(cardapio_atual)
            return redirect(url_for('configuracoes'))

        elif action == 'add_item':
            # --- Adicionar Item ---
            target_category = request.form['target_category']
            item_name = request.form['item_name'].strip()
            item_description = request.form['item_description'].strip()
            
            try:
                valor_str = request.form['item_value'].replace(',', '.').strip()
                item_value = float(valor_str)
            except ValueError:
                item_value = 0.0

            if target_category in cardapio_atual and item_name:
                novo_produto = {
                    "nome": item_name,
                    "descricao": item_description,
                    "valor": item_value
                }
                cardapio_atual[target_category].append(novo_produto)
                salvar_catalogo(cardapio_atual)
            return redirect(url_for('configuracoes'))

        elif action == 'edit_existing':
            # --- Salvar Edição de Campos de Texto ---
            categorias_chaves = list(cardapio_atual.keys())
            novas_categorias = {} 

            for chave in categorias_chaves:
                nomes = request.form.getlist(f'nome_{chave}')
                descricoes = request.form.getlist(f'descricao_{chave}')
                valores = request.form.getlist(f'valor_{chave}')

                produtos_da_categoria = []
                num_produtos = min(len(nomes), len(descricoes), len(valores))
                
                for i in range(num_produtos):
                    try:
                        valor = float(valores[i].replace(',', '.').strip())
                    except ValueError:
                        valor = 0.0

                    produtos_da_categoria.append({
                        "nome": nomes[i],
                        "descricao": descricoes[i],
                        "valor": valor
                    })
                
                novas_categorias[chave] = produtos_da_categoria
                
            salvar_catalogo(novas_categorias)
            
            return redirect(url_for('configuracoes', status='saved'))

        return redirect(url_for('configuracoes'))
        
    # Pega o status da URL (saved ou deleted) para mostrar a mensagem
    # O status agora é pego diretamente na rota GET, se presente.
    status = request.args.get('status') 
    
    return render_template('configuracoes.html', cardapio=cardapio_atual, status=status)