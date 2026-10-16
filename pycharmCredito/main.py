
from flask import Flask, render_template, request, flash, redirect, url_for, session
from datetime import date
from decimal import Decimal, InvalidOperation
from flask_bcrypt import Bcrypt
import fdb

# CONFIGURAÇÃO DO FLASK
app = Flask(__name__, template_folder="Templates", static_folder="Static", static_url_path="/static")
bcrypt = Bcrypt(app)
app.config["SECRET_KEY"] = "Chavesdfglkjhgfdshjkjhgfdcvbmnb"
# CONEXÃO COM O BANCO
host = "localhost"
database = r"C:\Users\Aluno\Downloads\ARO-ESTUDOS-main\ARO-ESTUDOS-main\BANCO.FDB"
user = "SYSDBA"
password = "sysdba"

con = fdb.connect(
    host=host,
    database=database,
    user=user,
    password=password
)

# VERIFICAÇÃO DE SENHA FORTE

def senha_forte(senha):
    if len(senha) < 8 :
        return False

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_simbolo = False

    # Verifica cada caractere da senha.
    for caractere in senha:
        if caractere.isupper():
            tem_maiuscula = True
        if caractere.islower():
            tem_minuscula = True
        if caractere.isdigit():
            tem_numero = True
        if caractere in "!@#%":
            tem_simbolo = True
        if caractere.isspace():
            return False

    if tem_maiuscula and tem_minuscula and tem_numero and tem_simbolo:
        return True
    else:
        return False


# VALIDAR VALOR DAS RECEITAS

def valor_positivo(texto):
    # Aceita 100.50 ou 100,50, sem permitir valores negativos ou zero.
    texto = str(texto).strip().replace(",", ".")
    valor = Decimal(texto)
    if not valor.is_finite() or valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    return valor


# VERIFICA A SENHA CRIPTOGRAFADA

def verificar_senha(senha_hash, senha):
    return bcrypt.check_password_hash(senha_hash, senha)

# VERIFICA SE O USUÁRIO ESTÁ AUTENTICADO

def usuario_autenticado():
    if "id_usuario" not in session:
        return False

    cursor = con.cursor()
    try:
        # Consulta somente a conta que está na sessão.
        cursor.execute("""SELECT ATIVO, BLOQUEADO_LOGIN FROM USUARIO
                          WHERE ID_USUARIO = ?""", (session["id_usuario"],))
        usuario = cursor.fetchone()
        if usuario:
            if usuario[0] == 1 and (usuario[1] or 0) == 0:
                return True

        return False
    except Exception:
        return False
    finally:
        con.rollback()
        cursor.close()

# PÁGINA INICIAL DO SITE

@app.route("/")
def landing():
    return render_template("landing.html")

# PÁGINA DO USUÁRIO LOGADO

@app.route("/novo")
def novo():
    if not usuario_autenticado():
        session.clear()

        flash("Precisa estar logado e ativo!", "error")

        return redirect(url_for("login"))

    if "nome_usuario" not in session:
        session.clear()

        flash("Faça login novamente!", "error")

        return redirect(url_for("login"))

    return render_template("inicio.html", usuario=session["nome_usuario"])

# PÁGINA DE CADASTRO

@app.route("/cadastro")
def pagina_cadastro():
    return render_template("cadastro.html")

# CADASTRAR USUÁRIO

@app.route("/cadastro", methods=["POST"])
def cadastro():
    nome = request.form.get("nome", "").strip()

    email = request.form.get("email", "").strip()

    senha = request.form.get("senha", "")

    confirmar_senha = request.form.get("confirmar_senha", "")

    tipo_usuario = 7

    if not nome or not email or not senha or not confirmar_senha:
        flash("Preencha todos os campos!", "error")

        return redirect(url_for("pagina_cadastro"))

    if senha != confirmar_senha:
        flash("A senha e a confirmação de senha não são iguais!", "error")

        return redirect(url_for("pagina_cadastro"))

    if not senha_forte(senha):
        flash(
            "A senha deve ter pelo menos 8 caracteres, letras maiúsculas, minúsculas, números e um símbolo (! @ # %) e sem espaços. ",
            "error"
        )

        return redirect(url_for("pagina_cadastro"))

    cursor = con.cursor()

    try:
        # VERIFICA E-MAIL REPETIDO

        cursor.execute("""SELECT ID_USUARIO FROM USUARIO WHERE UPPER(EMAIL) = UPPER(?)""", (email,))

        if cursor.fetchone():
            flash("Este e-mail já está cadastrado!", "error")

            return redirect(url_for("pagina_cadastro"))

        # CRIPTOGRAFA A SENHA

        senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

        # SALVA O USUÁRIO NO BANCO

        cursor.execute("""INSERT INTO USUARIO (NOME, EMAIL, SENHA, TIPO_USUARIO) VALUES (?, ?, ?, ?)""", (
            nome,
            email,
            senha_hash,
            tipo_usuario
        ))

        con.commit()

        flash("Cadastro realizado com sucesso!", "success")

        return redirect(url_for("login"))

    except Exception as e:
        con.rollback()

        flash(f"Erro ao cadastrar: {e}", "error")

        return redirect(url_for("pagina_cadastro"))

    finally:
        con.rollback()
        cursor.close()

# PÁGINA DE LOGIN

@app.route("/login")
def login():
    return render_template("login.html")

# ENTRAR NA CONTA

@app.route("/login", methods=["POST"])
def entrar_usuario():
    email = request.form.get("email", "").strip()

    senha = request.form.get("senha", "")

    if not email or not senha:
        flash("Preencha o e-mail e a senha!", "error")
        return redirect(url_for("login"))

    cursor = con.cursor()
    try:
        # Busca os dados e as tentativas da conta informada.
        cursor.execute("""SELECT ID_USUARIO, NOME, SENHA, ATIVO,
                          TENTATIVAS_LOGIN, BLOQUEADO_LOGIN
                          FROM USUARIO WHERE UPPER(EMAIL) = UPPER(?)""", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            flash("E-mail ou senha incorretos!", "error")
            return redirect(url_for("login"))

        id_usuario, nome, senha_hash, ativo, tentativas, bloqueado = usuario

        if ativo != 1:
            flash("Usuário inativo!", "error")
            return redirect(url_for("login"))

        tentativas = tentativas or 0
        bloqueado = bloqueado or 0

        if bloqueado == 1 or tentativas >= 3:
            flash("Usuário bloqueado! Solicite o desbloqueio.", "error")
            return redirect(url_for("login"))

        # Se acertar a senha, zera apenas as tentativas desta conta.
        if verificar_senha(senha_hash, senha):
            cursor.execute("""UPDATE USUARIO SET TENTATIVAS_LOGIN = 0
                              WHERE ID_USUARIO = ?""", (id_usuario,))
            con.commit()

            session.clear()
            session["id_usuario"] = id_usuario
            session["nome_usuario"] = nome
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("novo"))

        # Se errar a senha, soma uma tentativa.
        tentativas = tentativas + 1

        if tentativas >= 3:
            bloqueado = 1
            flash("Usuário bloqueado após 3 tentativas!", "error")
        else:
            flash(f"Senha incorreta! Restam {3 - tentativas} tentativa(s).", "error")

        # O ID no WHERE garante que somente esta conta será alterada.
        cursor.execute("""UPDATE USUARIO
                          SET TENTATIVAS_LOGIN = ?, BLOQUEADO_LOGIN = ?
                          WHERE ID_USUARIO = ?""", (tentativas, bloqueado, id_usuario))
        con.commit()
        return redirect(url_for("login"))

    except Exception:
        con.rollback()
        flash("Não foi possível entrar. Verifique a conexão com o banco.", "error")
        return redirect(url_for("login"))
    finally:
        # Encerra a consulta, inclusive quando o login é recusado.
        con.rollback()
        cursor.close()

# LOGOUT

@app.route("/logout", methods=["POST"])
def logout():
    if "id_usuario" not in session:
        flash("Precisa estar logado!", "error")

        return redirect(url_for("login"))

    session.clear()

    flash("Você saiu da sua conta!", "success")

    return redirect(url_for("login"))

# EDITAR USUÁRIO

@app.route("/editar_usuario")
def editar_usuario():
    if not usuario_autenticado():
        session.clear()

        flash("Precisa estar logado e ativo!", "error")

        return redirect(url_for("login"))

    cursor = con.cursor()
    try:
        cursor.execute("""SELECT ID_USUARIO, NOME, EMAIL, TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO = ?""", (session["id_usuario"],))

        usuario = cursor.fetchone()

        if not usuario:
            session.clear()

            flash("Usuário não encontrado!", "error")

            return redirect(url_for("login"))

        return render_template("editar_usuario.html", usuario=usuario)
    finally:
        con.rollback()
        cursor.close()

# SALVAR EDIÇÃO DO USUÁRIO

@app.route("/salvar_edicao", methods=["POST"])
def salvar_edicao():
    if not usuario_autenticado():
        session.clear()

        flash("Precisa estar logado e ativo!", "error")

        return redirect(url_for("login"))

    nome = request.form.get("nome", "").strip()

    email = request.form.get("email", "").strip()

    senha = request.form.get("senha", "")

    confirmar_senha = request.form.get("confirmar_senha", "")

    if not nome or not email:
        flash("Preencha todos os campos!", "error")

        return redirect(url_for("editar_usuario"))

    if senha != confirmar_senha:
        flash("A nova senha e a confirmação não são iguais!", "error")

        return redirect(url_for("editar_usuario"))

    if senha and not senha_forte(senha):
        flash(
            "A nova senha deve ter pelo menos 8 caracteres, letras maiúsculas, minúsculas, números e um símbolo (! @ # %), sem espaços.",
            "error")

        return redirect(url_for("editar_usuario"))

    cursor = con.cursor()
    try:
        # VERIFICA E-MAIL REPETIDO

        cursor.execute("""SELECT ID_USUARIO FROM USUARIO WHERE UPPER(EMAIL) = UPPER(?) AND ID_USUARIO <> ?""", (email, session["id_usuario"]))

        if cursor.fetchone():
            flash("Este e-mail já está cadastrado!", "error")

            return redirect(url_for("editar_usuario"))

        # ATUALIZA OS DADOS

        if senha:
            cursor.execute("""SELECT SENHA, SENHA_ANTERIOR1, SENHA_ANTERIOR2, SENHA_ANTERIOR3 FROM USUARIO WHERE ID_USUARIO = ?""", (session["id_usuario"],))

            dados = cursor.fetchone()

            if not dados:
                session.clear()

                flash("Usuário não encontrado!", "error")

                return redirect(url_for("login"))

            # VERIFICA AS SENHAS ANTERIORES

            for senha_antiga in dados:
                if senha_antiga:
                    if verificar_senha(senha_antiga, senha):
                        flash(
                            "Você não pode reutilizar a senha atual nem as 3 anteriores!",
                            "error"
                        )

                        return redirect(url_for("editar_usuario"))

            # CRIPTOGRAFA A NOVA SENHA

            senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

            # ATUALIZA OS DADOS E O HISTÓRICO

            cursor.execute("""UPDATE USUARIO SET NOME = ?, EMAIL = ?, SENHA_ANTERIOR3 = SENHA_ANTERIOR2, SENHA_ANTERIOR2 = SENHA_ANTERIOR1, SENHA_ANTERIOR1 = SENHA, SENHA = ? WHERE ID_USUARIO = ?""", (
                nome,
                email,
                senha_hash,
                session["id_usuario"]
            ))

        else:
            cursor.execute("""UPDATE USUARIO SET NOME = ?, EMAIL = ? WHERE ID_USUARIO = ?""", (
                nome,
                email,
                session["id_usuario"]
            ))

        # SALVA NO BANCO

        con.commit()

        session["nome_usuario"] = nome

        flash("Usuário atualizado com sucesso!", "success")

        return redirect(url_for("novo"))

    except Exception as e:
        con.rollback()

        flash(f"Erro ao editar usuário: {e}", "error")

        return redirect(url_for("editar_usuario"))
    finally:
        con.rollback()
        cursor.close()

# SALDO ATUAL

@app.route("/saldo_atual")
def saldo_atual():
    if not usuario_autenticado():
        session.clear()
        flash("Faça login para acessar esta página!", "error")
        return redirect(url_for("login"))

    return render_template("saldo_atual.html")


# PÁGINA DO PERFIL DO USUÁRIO

@app.route("/perfil")
def perfil():
    if not usuario_autenticado():
        flash("Precisa estar logado!", "error")

        return redirect(url_for("login"))

    cursor = con.cursor()
    try:
        cursor.execute("""SELECT ID_USUARIO, NOME, EMAIL FROM USUARIO
            WHERE ID_USUARIO = ?""", (session["id_usuario"],))

        usuario = cursor.fetchone()

        if not usuario:
            flash("Usuário não encontrado!", "error")
            return redirect(url_for("login"))

        return render_template("perfil.html", usuario=usuario)

    finally:
        con.rollback()
        cursor.close()

# CADASTRAR, EDITAR E LISTAR RECEITAS

@app.route("/receitas", methods=["GET", "POST"])
@app.route("/receitas/<int:id_registro>/editar", methods=["GET", "POST"])
def receitas(id_registro=None):
    # Verifica se o usuário está logado.
    if not usuario_autenticado():
        session.clear()
        flash("Faça login para continuar.", "error")
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    cursor = con.cursor()
    registro = None

    try:
        # Busca a receita que será editada.
        if id_registro is not None:
            cursor.execute("""
                SELECT ID_REGISTRO, DESCRICAO, VALOR, DATA_MOVIMENTO
                FROM ARO_RECEITA
                WHERE ID_REGISTRO = ? AND ID_USUARIO = ?
            """, (id_registro, id_usuario))

            registro = cursor.fetchone()

            if registro is None:
                flash("Registro não encontrado.", "error")
                return redirect(url_for("receitas"))

        # Recebe os dados enviados pelo formulário.
        if request.method == "POST":
            descricao = request.form.get("descricao", "").strip()
            valor = valor_positivo(request.form.get("valor", ""))
            data_movimento = date.fromisoformat(
                request.form.get("data", "")
            )

            if descricao == "" or len(descricao) > 100:
                flash("Informe uma descrição de até 100 caracteres.", "error")
                return redirect(
                    url_for("receitas", id_registro=id_registro)
                )

            if registro is None:
                # Cadastra uma nova receita.
                cursor.execute("""
                    INSERT INTO ARO_RECEITA
                    (ID_USUARIO, DESCRICAO, VALOR, DATA_MOVIMENTO)
                    VALUES (?, ?, ?, ?)
                """, (id_usuario, descricao, valor, data_movimento))

                mensagem = "Receita cadastrada com sucesso!"

            else:
                # Atualiza a receita do usuário.
                cursor.execute("""
                    UPDATE ARO_RECEITA
                    SET DESCRICAO = ?, VALOR = ?, DATA_MOVIMENTO = ?
                    WHERE ID_REGISTRO = ? AND ID_USUARIO = ?
                """, (
                    descricao, valor, data_movimento,
                    id_registro, id_usuario
                ))

                mensagem = "Receita atualizada com sucesso!"

            # Salva a receita no banco.
            con.commit()

            flash(mensagem, "success")
            return redirect(url_for("receitas"))

        # Lista as receitas do usuário.
        cursor.execute("""
            SELECT ID_REGISTRO, DESCRICAO, VALOR, DATA_MOVIMENTO
            FROM ARO_RECEITA
            WHERE ID_USUARIO = ?
            ORDER BY DATA_MOVIMENTO DESC, ID_REGISTRO DESC
        """, (id_usuario,))

        registros = cursor.fetchall()

        return render_template(
            "receitas.html",
            registros=registros,
            registro=registro,
            hoje=date.today().isoformat()
        )

    except (ValueError, InvalidOperation):
        con.rollback()
        flash("Confira a data e informe um valor positivo válido.", "error")
        return redirect(url_for("receitas", id_registro=id_registro))

    except Exception as e:
        con.rollback()
        # Mostra o erro real no terminal para facilitar a correção.
        app.logger.exception("Erro na página de receitas", e)
        flash("Ocorreu um erro na página de receitas. Confira o terminal.", "error")
        # Evita voltar à mesma página quando o erro ocorre ao abri-la.
        return redirect(url_for("novo"))

    finally:
        # Encerra qualquer transação pendente e fecha o cursor.
        con.rollback()
        cursor.close()


# EXCLUIR RECEITA

@app.route("/receitas/<int:id_registro>/excluir", methods=["POST"])
def excluir_receita(id_registro):
    if not usuario_autenticado():
        session.clear()
        flash("Faça login para continuar.", "error")
        return redirect(url_for("login"))

    id_usuario = session["id_usuario"]
    cursor = con.cursor()

    try:
        # Busca a receita do usuário.
        cursor.execute("""
            SELECT DATA_MOVIMENTO
            FROM ARO_RECEITA
            WHERE ID_REGISTRO = ? AND ID_USUARIO = ?
        """, (id_registro, id_usuario))

        registro = cursor.fetchone()

        if registro is None:
            flash("Registro não encontrado.", "error")

        else:
            # Exclui apenas a receita pertencente ao usuário.
            cursor.execute("""
                DELETE FROM ARO_RECEITA
                WHERE ID_REGISTRO = ? AND ID_USUARIO = ?
            """, (id_registro, id_usuario))

            con.commit()

            flash("Receita excluída com sucesso!", "success")

    except Exception:
        con.rollback()
        app.logger.exception("Erro ao excluir receita")
        flash("Não foi possível excluir a receita.", "error")

    finally:
        con.rollback()
        cursor.close()

    return redirect(url_for("receitas"))


@app.route('/admin')
def admin():
   return render_template('index.html')


if __name__ == "__main__":
    # A conexão é compartilhada: processa uma requisição por vez.
    app.run(debug=True, threaded=False)
