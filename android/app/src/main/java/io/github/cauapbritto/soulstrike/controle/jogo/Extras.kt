package io.github.cauapbritto.soulstrike.controle.jogo

import org.json.JSONArray
import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

/*
 * As novidades do app que conversam com o jogo (v1.60.0): o apelido que a TV mostra no lugar de
 * P1, o resumo da partida, o MAPA da fase (ou da Casa) e o CADERNO DE SEGREDOS.
 */

/** As letras que a fonte do jogo desenha (as mesmas do NICK_LETTERS do jogo). */
private const val LETRAS_DO_APELIDO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ÁÀÂÃÉÊÍÓÔÕÚÜÇ -_.!?"

const val MAX_APELIDO = 10

/** O apelido como a TV mostra: maiúsculas, só as letras da fonte, até 10 (igual ao clean_nick do jogo). */
fun limparApelido(texto: String): String {
    val grande = Normalizer.normalize(texto, Normalizer.Form.NFC).uppercase(Locale.ROOT)
    val trocado = buildString { for (c in grande) append(if (c in LETRAS_DO_APELIDO) c else ' ') }
    return trocado.split(' ').filter { it.isNotEmpty() }.joinToString(" ").take(MAX_APELIDO).trim()
}

/** [["GOLS", "3"], ...] do jogo para pares. */
private fun pares(a: JSONArray?): List<Pair<String, String>> {
    if (a == null) return emptyList()
    return (0 until a.length()).mapNotNull { i ->
        val par = a.optJSONArray(i) ?: return@mapNotNull null
        if (par.length() < 2) null else par.optString(0) to par.optString(1)
    }
}

/** O resumo da partida que acabou (resumo.py do jogo): só na tela de resultado. */
class Resumo(val o: JSONObject) {
    val titulo = o.texto("title")
    val cor = o.texto("color", "#ffd75a")
    val placar: String? = o.textoOuNulo("score")
    val linhas: List<Pair<String, String>> = pares(o.optJSONArray("lines"))
    val recordes: List<String> = o.optJSONArray("records")?.let { a -> (0 until a.length()).map { a.optString(it) } }
        ?.filter { it.isNotEmpty() } ?: emptyList()
    val destaque: Destaque? = o.optJSONObject("mvp")?.let {
        Destaque(it.inteiroOuNulo("slot") ?: 0, it.texto("label"), it.texto("hero"))
    }
    val jogadores: Map<Int, Jogador> = buildMap {
        val p = o.optJSONObject("players")
        if (p != null) for (k in p.keys()) {
            val j = p.optJSONObject(k) ?: continue
            val n = k.toIntOrNull() ?: continue
            val venceu = if (!j.has("won") || j.isNull("won")) null else j.optBoolean("won")
            put(n, Jogador(j.texto("label"), j.texto("hero"), venceu, pares(j.optJSONArray("lines"))))
        }
    }

    data class Destaque(val vaga: Int, val rotulo: String, val heroi: String)
    data class Jogador(val rotulo: String, val heroi: String, val venceu: Boolean?, val linhas: List<Pair<String, String>>)
}

/** O MAPA (mapa_celular.py do jogo): caixas, marcas e jogadores em quadrados do mapa. */
class MapaJogo(val o: JSONObject) {
    val titulo = o.texto("title")
    val sub = o.texto("sub")
    val largura = o.optDouble("w", 1.0).toFloat().coerceAtLeast(1f)
    val altura = o.optDouble("h", 1.0).toFloat().coerceAtLeast(1f)
    val caixas: List<Caixa> = o.optJSONArray("boxes").objetos().map {
        Caixa(
            it.optDouble("x").toFloat(), it.optDouble("y").toFloat(), it.optDouble("w").toFloat(), it.optDouble("h").toFloat(),
            it.textoOuNulo("fill"), it.textoOuNulo("line"), it.textoOuNulo("label"), it.textoOuNulo("mark"),
            it.optBoolean("done"),
        )
    }
    val marcas: List<Marca> = o.optJSONArray("marks").objetos().map {
        Marca(it.optDouble("x").toFloat(), it.optDouble("y").toFloat(), it.texto("color", "#ffffff"),
            it.texto("kind", "dot"), it.texto("label"))
    }
    val jogadores: List<Ponto> = o.optJSONArray("players").objetos().map {
        Ponto(it.optDouble("x").toFloat(), it.optDouble("y").toFloat(), it.optInt("slot"), it.texto("color", "#ffffff"),
            it.texto("label"), it.optBoolean("down"))
    }

    data class Caixa(
        val x: Float, val y: Float, val w: Float, val h: Float,
        val fundo: String?, val borda: String?, val nome: String?, val sinal: String?, val limpa: Boolean,
    )

    data class Marca(val x: Float, val y: Float, val cor: String, val tipo: String, val nome: String)
    data class Ponto(val x: Float, val y: Float, val vaga: Int, val cor: String, val nome: String, val caido: Boolean)
}

/** O CADERNO DE SEGREDOS (os achados com nome, os que faltam com a dica). */
class Caderno(val o: JSONObject) {
    val achados = o.optInt("found")
    val total = o.optInt("total")
    val paginas: List<Pagina> = o.optJSONArray("pages").objetos().map { p ->
        Pagina(p.texto("place"), p.optJSONArray("items").objetos().map { Segredo(it.optBoolean("found"), it.texto("text")) })
    }

    data class Pagina(val lugar: String, val segredos: List<Segredo>)
    data class Segredo(val achado: Boolean, val texto: String)
}
