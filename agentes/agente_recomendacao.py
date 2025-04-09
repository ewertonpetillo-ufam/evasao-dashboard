class AgenteRecomendacao:
    def __init__(self):
        pass

    def recomendar(self, predicao):
        if predicao["previsao"] == "Evadido":
            return [
                "Encaminhar para apoio pedagógico",
                "Avaliar situação socioeconômica",
                "Contato com tutor ou coordenador"
            ]
        else:
            return [
                "Reforçar pontos fortes identificados",
                "Oferecer oportunidades de monitoria ou pesquisa"
            ]
