"""Planted-error corpus for the manual immersion eval.

Five entries. ``errors`` are substrings a minimal correction should contain.
``traps`` are already-correct phrases that must survive unchanged.
"""

CORPUS = {
    "S1": dict(
        l2="es",
        l1="en",
        text=(
            "El sábado yo fui a la playa con mis amigos. Nosotros comimos mucho mariscos y el agua estaba muy frío. "
            "Despues, yo estaba muy cansado pero feliz porque es la primera vez que yo nado en el mar este año."
        ),
        errors={
            "mucho mariscos": ["muchos mariscos", "mucho marisco"],
            "agua ... frío": ["fría"],
            "Despues": ["Después"],
            "es la primera vez que yo nado": ["era la primera vez", "fue la primera vez"],
        },
        traps={},
    ),
    "S2": dict(
        l2="es",
        l1="en",
        text=(
            "Ayer fui a una fiesta en la casa de mi jefe. Estaba muy embarazada porque olvidé el nombre de su esposa. "
            "Mi jefe es muy sensible y no se enojó. Al final, realicé que la fiesta era para su cumpleaños y yo no traje nada."
        ),
        errors={
            "embarazada (false friend)": ["avergonzada", "apenada"],
            "realicé (false friend)": ["me di cuenta"],
            "sensible (likely meant understanding)": [
                "comprensivo",
                "comprensiva",
                "sensato",
                "amable",
                "buena onda",
                "tranquilo",
            ],
        },
        traps={
            "olvidé el nombre": ["olvidé el nombre"],
            "era para su cumpleaños": ["era para su cumpleaños", "era por su cumpleaños"],
        },
    ),
    "S3": dict(
        l2="es",
        l1="en",
        text=(
            "Mi hermana es muy aburrida hoy porque está lloviendo. Quiero que ella viene conmigo al cine para ver una película nueva. "
            "Compré los boletos por 10 euros cada uno. La película es en el centro."
        ),
        errors={
            "es aburrida -> está aburrida (bored)": ["está muy aburrida", "está aburrida"],
            "quiero que viene -> venga": ["venga"],
        },
        traps={
            "por 10 euros (correct)": ["por 10 euros", "por diez euros"],
            "es en el centro (event location, correct)": ["es en el centro"],
        },
    ),
    "J1": dict(
        l2="ja",
        l1="en",
        text=(
            "昨日、友達と映画を見に行きました。映画はとても面白いでした。そして、レストランで寿司を食べるました。私の家に猫が二本います。"
        ),
        errors={
            "面白いでした": ["面白かった"],
            "食べるました": ["食べました"],
            "二本 (counter)": ["二匹"],
        },
        traps={"見に行きました": ["見に行きました"]},
    ),
    "J2": dict(
        l2="ja",
        l1="en",
        text=(
            "誕生日に先生が私に本をあげました。とても嬉しいでした。私は先生にお礼の手紙を書いてくれました。来週、先生と会うつもりです。"
        ),
        errors={
            "あげました -> くれました (direction)": ["くれました"],
            "嬉しいでした": ["嬉しかった", "うれしかった"],
            "書いてくれました -> 書きました (direction)": ["手紙を書きました", "書きました", "書いてあげました"],
        },
        traps={"会うつもりです": ["会うつもりです", "会う予定です"]},
    ),
}

LOCALE = {"es": "es-ES", "en": "en-US", "ja": "ja-JP", "ar": "ar-SA", "fr": "fr-FR"}
NAMES = {"es": "Spanish", "en": "English", "ja": "Japanese", "ar": "Arabic", "fr": "French"}
