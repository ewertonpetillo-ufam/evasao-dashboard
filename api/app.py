from binascii import Error
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import cx_Oracle
import pandas as pd
import pickle
from config import *
import logging
from sklearn.preprocessing import LabelEncoder
import shap


with open("./model/RF_Predict_Sauim_v3.pkl", "rb") as f:
    model = pickle.load(f)

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import re

def remove_illegal_characters(data):
    # Remover caracteres ilegais com uma expressão regular
    illegal_characters_re = re.compile(r'[\x00-\x1F\x7F-\x9F]')
    if isinstance(data, str):
        return illegal_characters_re.sub('', data)
    return data


def get_db_connection():
    config = str_acesso()

    dsn_tns = cx_Oracle.makedsn(config['host'], config['port'], config['sid'])
    connection = cx_Oracle.connect(
            'dbsm', 
            'wobistdu', 
            dsn_tns, 
            encoding="UTF-8",
            nencoding="UTF-8"
    )
    return connection

def getDadosAluno(matricula):
    logger.info("Carregando Dados do Aluno...")

    try:
        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta SQL (substitua pela sua consulta)
        query = """
        WITH Evasoes AS (
            SELECT
                ca.ID_ALUNO,
                ca.ANO_EVASAO,
                ca.FORMA_EVASAO_ITEM
            FROM CURSOS_ALUNOS ca
                    JOIN VERSOES_CURSOS vc ON ca.ID_VERSAO_CURSO = vc.ID_VERSAO_CURSO
                    JOIN CURSOS c ON vc.ID_CURSO = c.ID_CURSO
            WHERE c.NIVEL_CURSO_ITEM IN (3,14,15,16,17,18)
            AND ca.FORMA_EVASAO_ITEM IN (12, 24)  -- Considerando apenas desistências
        ),
        Ingressos AS (
            SELECT
                ca.ID_ALUNO,
                max(ca.ANO_INGRESSO) AS ANO_INGRESSO
            FROM CURSOS_ALUNOS ca
            JOIN VERSOES_CURSOS vc ON ca.ID_VERSAO_CURSO = vc.ID_VERSAO_CURSO
            JOIN CURSOS c ON vc.ID_CURSO = c.ID_CURSO
            WHERE c.NIVEL_CURSO_ITEM IN (3,14,15,16,17,18) and ca.FORMA_EVASAO_ITEM in (1)
            GROUP BY ca.ID_ALUNO
        ),
        Desistencias_Filtradas AS (
        SELECT
            e.ID_ALUNO,
            COUNT(*) AS total_desistencias
        FROM Evasoes e
        LEFT JOIN Ingressos i ON e.ID_ALUNO = i.ID_ALUNO
        WHERE i.ID_ALUNO IS NULL OR i.ANO_INGRESSO - e.ANO_EVASAO > 1
        GROUP BY e.ID_ALUNO
        ),
        Assistencia_Estudantil as (
            SELECT
                COUNT(*) as auxilio_estudantil,
                tt1.ID_CURSO_ALUNO
            FROM UFAM_AE.AE_INSCRICAO tt1
            INNER JOIN UFAM_AE.AE_INSC_EDITAL tt2 ON tt1.ID_INSCRICAO = tt2.ID_INSCRICAO
            INNER JOIN DBSM.CURSOS_ALUNOS ca on tt1.ID_CURSO_ALUNO = ca.ID_CURSO_ALUNO
            WHERE tt1.STATUS_ITEM in (2,5,6)
            GROUP BY tt1.ID_CURSO_ALUNO
            UNION
            select
                count(*) as auxilio_estudantil,
                i.ID_CURSO_ALUNO
            from ASSIST_SOCIAL_INSC_EDITAL ie
            inner join ASSIST_SOCIAL_INSCRICAO i on i.ID_INSCRICAO = ie.ID_INSCRICAO
            inner join ASSIST_SOCIAL_EDITAL e on e.ID_EDITAL = ie.ID_EDITAL
            where ie.STATUS in (2,5,6)
            group by i.ID_CURSO_ALUNO
        )
        SELECT
            t1.FORMA_INGRE_ITEM,
            t3.ID_CURSO AS CURSO,
            t3.NIVEL_CURSO_ITEM,
            t3.LOCAL_FISICO_ITEM,
            t3.TURNO_CURSO_ITEM,
            t5.ESTADO_CIVIL_ITEM,
            COALESCE(ae.auxilio_estudantil, 0) AS AUXILIO,
            (
                (1.0 - ((
                            select count(*) from curriculo_aluno t11
                            where t11.id_curso_aluno = t1.id_curso_aluno
                            and t11.situacao_ocor <> 'E'
                            and t11.situacao_item in (3)
                        ) /
                        case when (
                                    select count(*) as ch from curriculo_aluno t11
                                    where t11.id_curso_aluno = t1.id_curso_aluno
                                        and t11.situacao_ocor <> 'E'
                                ) > 0 then(
                            select count(*) as ch from curriculo_aluno t11
                            where t11.id_curso_aluno = t1.id_curso_aluno
                            and t11.situacao_ocor <> 'E'
                        )
                            else 1 end)) * 100.0
                ) as perc_frequencia,
            ((
                select count(*) from curriculo_aluno t11
                where t11.id_curso_aluno = t1.id_curso_aluno
                and t11.situacao_ocor <> 'E'
                and t11.situacao_item = 2
            ) / (case when (
                                select count(*)
                                from CURRICULO_ALUNO
                                where SITUACAO_OCOR <> 'E'
                                and SITUACAO_ITEM not in 10
                                and ID_CURSO_ALUNO = t1.id_curso_aluno
                                and ID_ATIV_CURRIC not in (28644,30779)
                            ) > 0 then(
                select count(*)
                from CURRICULO_ALUNO
                where SITUACAO_OCOR <> 'E'
                and SITUACAO_ITEM not in 10
                and ID_CURSO_ALUNO = t1.id_curso_aluno
                and ID_ATIV_CURRIC not in (28644,30779)
            ) else 1 end) * 100) as perc_disc_reprovadas_notas,
            ((
                select count(*) from curriculo_aluno t11
                where t11.id_curso_aluno = t1.id_curso_aluno
                and t11.situacao_ocor <> 'E'
                and t11.situacao_item = 3
            ) / (case when (
                                select count(*)
                                from CURRICULO_ALUNO
                                where SITUACAO_OCOR <> 'E'
                                and SITUACAO_ITEM not in 10
                                and ID_CURSO_ALUNO = t1.id_curso_aluno
                                and ID_ATIV_CURRIC not in (28644,30779)
                            ) > 0 then(
                select count(*)
                from CURRICULO_ALUNO
                where SITUACAO_OCOR <> 'E'
                and SITUACAO_ITEM not in 10
                and ID_CURSO_ALUNO = t1.id_curso_aluno
                and ID_ATIV_CURRIC not in (28644,30779)
            ) else 1 end) * 100) as perc_disc_repr_frequencia,
            ((
                select count(*) from curriculo_aluno t11
                                        join curriculo_aluno t100 on t11.ID_CURRIC_ALUNO = t100.ID_CURRIC_ALUNO
                                        join estrutura_curric t101 on t100.ID_ESTRUTURA_CUR = t101.ID_ESTRUTURA_CUR
                where t11.id_curso_aluno = t1.id_curso_aluno
                and t11.situacao_ocor <> 'E'
                and t11.situacao_item = 5
                and t101.DESCR_ESTRUTURA <> 'OPTATIVAS'
            ) / (case when (
                                select count(*)
                                from CURRICULO_ALUNO
                                where SITUACAO_OCOR <> 'E'
                                and SITUACAO_ITEM not in 10
                                and ID_CURSO_ALUNO = t1.id_curso_aluno
                                and ID_ATIV_CURRIC not in (28644,30779)
                            ) > 0 then(
                select count(*)
                from CURRICULO_ALUNO
                where SITUACAO_OCOR <> 'E'
                and SITUACAO_ITEM not in 10
                and ID_CURSO_ALUNO = t1.id_curso_aluno
                and ID_ATIV_CURRIC not in (28644,30779)
            ) else 1 end) * 100) as perc_disc_trancadas,
            (
                select count(*) from curriculo_aluno t11
                                        join curriculo_aluno t100 on t11.ID_CURRIC_ALUNO = t100.ID_CURRIC_ALUNO
                                        join estrutura_curric t101 on t100.ID_ESTRUTURA_CUR = t101.ID_ESTRUTURA_CUR
                where t11.id_curso_aluno = t1.id_curso_aluno
                and t11.situacao_ocor <> 'E'
                and t11.situacao_item = 17
            ) as trancamentos_totais,
            (
                case when (select round(sum(t66.ch_total* t11.media_final)/ case when sum(t66.ch_total) = 0 then 1 else nvl(sum(t66.ch_total),1) end ,3) coeficente
                        from curriculo_aluno t11, cursos_alunos t22,
                                estrutura_curric t44, atividades_curric t66,
                                tab_estruturada t77, tab_estruturada t88
                        where t11.id_curso_aluno = t22.id_curso_aluno
                            and t11.id_estrutura_cur = t44.id_estrutura_cur
                            and t11.id_ativ_curric = t66.id_ativ_curric
                            and t11.periodo_tab = t77.cod_tabela
                            and t11.periodo_item = t77.item_tabela
                            and t11.situacao_tab = t88.cod_tabela
                            and t11.situacao_item = t88.item_tabela
                            and t11.situacao_ocor <> 'E'
                            and t11.situacao_item in (1,2,3,4,14,15)
                            and t22.matr_aluno = t1.matr_aluno
                ) is not null then (
                    select round(sum(t66.ch_total* t11.media_final)/ case when sum(t66.ch_total) = 0 then 1 else nvl(sum(t66.ch_total),1) end ,3) coeficente
                    from curriculo_aluno t11, cursos_alunos t22,
                        estrutura_curric t44, atividades_curric t66,
                        tab_estruturada t77, tab_estruturada t88
                    where t11.id_curso_aluno = t22.id_curso_aluno
                    and t11.id_estrutura_cur = t44.id_estrutura_cur
                    and t11.id_ativ_curric = t66.id_ativ_curric
                    and t11.periodo_tab = t77.cod_tabela
                    and t11.periodo_item = t77.item_tabela
                    and t11.situacao_tab = t88.cod_tabela
                    and t11.situacao_item = t88.item_tabela
                    and t11.situacao_ocor <> 'E'
                    and t11.situacao_item in (1,2,3,4,14,15)
                    and t22.matr_aluno = t1.matr_aluno
                ) else 0 end) as coeficiente,
            (
                select count(*)
                from cursos_alunos t110
                where t110.id_aluno = t1.id_aluno
                and t110.forma_evasao_item in (2,6,1004)
            ) as transferencias,
            COALESCE(df.total_desistencias, 0) AS desistencias, -- Ajuste para evitar NULL
            (
                SELECT COUNT(*)
                FROM cursos_alunos t110
                WHERE t110.id_aluno = t1.id_aluno
                AND t110.forma_evasao_item IN (7,25)
            ) AS jubilamentos
        FROM cursos_alunos t1
        JOIN versoes_cursos t2 ON t1.id_versao_curso = t2.id_versao_curso
        JOIN cursos t3 ON t2.id_curso = t3.id_curso
        JOIN alunos t5 ON t1.id_aluno = t5.id_aluno
        LEFT JOIN Desistencias_Filtradas df ON t1.ID_ALUNO = df.ID_ALUNO
        LEFT JOIN Evasoes ev ON t1.ID_ALUNO = ev.ID_ALUNO
        LEFT JOIN Ingressos ing ON t1.ID_ALUNO = ing.ID_ALUNO
        LEFT JOIN Assistencia_Estudantil ae on t1.ID_CURSO_ALUNO = ae.ID_CURSO_ALUNO
        WHERE
            t1.MATR_ALUNO = :matricula
       """
        
        cursor.execute(query, matricula=matricula)

        # Obter os dados
        columns = [col[0] for col in cursor.description]
        data = cursor.fetchall()

        cleaned_data = [[remove_illegal_characters(cell) for cell in row] for row in data]

        # Criar DataFrame do Pandas
        df = pd.DataFrame(cleaned_data, columns=columns)

        return df

    except Error as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/predict_aluno/<string:matricula>', methods=['GET'])
def get_predict(matricula):
    logger.info("Predict do Aluno")

    entrada = getDadosAluno(matricula)

    try:
        feature_importances = model.feature_importances_
        
        feature_names = entrada.columns.tolist()

        important_features = sorted(
            zip(feature_names, feature_importances), 
            key=lambda x: x[1], 
            reverse=True
        )

        label_encoder = LabelEncoder()
        for col in entrada.select_dtypes(include=['object']).columns:
            entrada[col] = label_encoder.fit_transform(entrada[col])
        y_pred = model.predict(entrada)
        proba_previsao = model.predict_proba(entrada)
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(entrada)

        shap_values_evadido = shap_values[:,:,0]
        df_sv_evadido = pd.DataFrame(shap_values_evadido,columns=entrada.columns)

        shap_values_formado = shap_values[:,:,1]
        df_sv_formado = pd.DataFrame(shap_values_formado,columns=entrada.columns)

        return{
            "previsao" : y_pred[0],
            "proba_evadido " : proba_previsao[0][0]*100,
            "proba_formado " : proba_previsao[0][1]*100,
            "peso_features_model" : important_features,
            "shap_evadido" :         df_sv_evadido.to_dict(orient="records"),
            "shap_formado" :         df_sv_formado.to_dict(orient="records")
        }


    except Error as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True) 
