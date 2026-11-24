package io.github.cauapbritto.soulstrike.controle.jogo

import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import org.json.JSONObject
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/** Posição e tamanho que o jogador escolheu para um botão (x e y de 0 a 1 dentro da zona). */
data class BotaoHud(val x: Float? = null, val y: Float? = null, val s: Float = 1f)

/**
 * O jeito do controle de um modo (AJUSTES DO CONTROLE): botões arrastados, tamanho, transparência,
 * analógico fixo ou solto e canhoto. Mesmo formato do site, guardado neste celular por modo.
 */
data class Hud(
    val botoes: Map<String, BotaoHud> = emptyMap(),
    val analogico: Offset? = null,
    val escalaAnalogico: Float = 1f,
    val fixo: Boolean = false,
    val opacidade: Float = 1f,
    val canhoto: Boolean = false,
) {
    fun json(): String {
        val o = JSONObject()
        val b = JSONObject()
        for ((k, v) in botoes) {
            val j = JSONObject().put("s", v.s.toDouble())
            if (v.x != null && v.y != null) j.put("x", v.x.toDouble()).put("y", v.y.toDouble())
            b.put(k, j)
        }
        o.put("btns", b)
        val a = analogico
        o.put("stick", if (a != null) JSONObject().put("x", a.x.toDouble()).put("y", a.y.toDouble()) else JSONObject.NULL)
        o.put("stickScale", escalaAnalogico.toDouble())
        o.put("fixed", fixo)
        o.put("opacity", opacidade.toDouble())
        o.put("lefty", canhoto)
        return o.toString()
    }

    companion object {
        fun carregar(texto: String?): Hud {
            if (texto.isNullOrEmpty()) return Hud()
            return try {
                val o = JSONObject(texto)
                val botoes = HashMap<String, BotaoHud>()
                val b = o.optJSONObject("btns")
                if (b != null) {
                    for (k in b.keys()) {
                        val j = b.optJSONObject(k) ?: continue
                        val x = if (j.has("x")) j.optDouble("x").toFloat() else null
                        val y = if (j.has("y")) j.optDouble("y").toFloat() else null
                        botoes[k] = BotaoHud(x, y, j.optDouble("s", 1.0).toFloat().coerceIn(0.7f, 1.5f))
                    }
                }
                val st = o.optJSONObject("stick")
                Hud(
                    botoes = botoes,
                    analogico = st?.let { Offset(it.optDouble("x", 0.3).toFloat(), it.optDouble("y", 0.7).toFloat()) },
                    escalaAnalogico = o.optDouble("stickScale", 1.0).toFloat().coerceIn(0.7f, 1.5f),
                    fixo = o.optBoolean("fixed"),
                    opacidade = o.optDouble("opacity", 1.0).toFloat().coerceIn(0.3f, 1f),
                    canhoto = o.optBoolean("lefty"),
                )
            } catch (e: Exception) {
                Hud()
            }
        }
    }
}

/** Cada modo guarda o seu jeito de botões. */
fun perfilDoModo(modo: String, hud: String): String = when {
    modo == "campaign" -> "campanha"
    modo == "luta" -> "luta"
    hud == "basket" -> "basquete"
    modo == "soccer" || hud == "soccer" -> "futebol"
    else -> "duelo"
}

fun nomeDoPerfil(perfil: String): String = when (perfil) {
    "campanha" -> "CAMPANHA"
    "luta" -> "LUTA"
    "basquete" -> "BASQUETE"
    "futebol" -> "FUTEBOL"
    else -> "DUELO"
}

enum class EstiloBotao { NORMAL, PRINCIPAL, MARCAR, HABILIDADE, SUPER }

/**
 * Um botão do controle. ``pos`` é o lugar no arco em volta do polegar: main (o grande, no canto),
 * w, nw, n (em volta) e ww, nn (os pequenos de fora).
 */
data class DefBotao(
    val acao: String,
    val pos: String,
    val rotulo: String,
    val icone: Int,
    val estilo: EstiloBotao = EstiloBotao.NORMAL,
    val desenhoDoJogo: String? = null,
)

/** Onde cada botão fica na tela (pixels da tela, dentro da camada do controle). */
data class PosBotao(val def: DefBotao, val x: Float, val y: Float, val tam: Float)

private val ANGULOS = mapOf("w" to 180.0, "nw" to 132.0, "n" to 84.0, "ww" to 156.0, "nn" to 108.0)

/** max(lo, min(hi, v)) como no site (nunca quebra quando lo > hi). */
fun lim(v: Float, lo: Float, hi: Float): Float = max(lo, min(hi, v))

/**
 * Os botões em arco em volta de onde o polegar direito descansa (o layoutButtons do site): o mais
 * usado grande no canto e os outros em volta, do tamanho que a tela pede. ``k`` = pixels da tela
 * por pixel do jogo.
 */
fun posicoesDosBotoes(defs: List<DefBotao>, zona: Rect, alturaTela: Float, k: Float, hud: Hud): List<PosBotao> {
    if (zona.width <= 0f || zona.height <= 0f) return emptyList()
    val zw = zona.width / k
    val zh = zona.height / k
    val vh = alturaTela / k
    val grande = lim(vh * 0.31f, 84f, 128f)
    val externos = defs.any { it.pos == "ww" || it.pos == "nn" }
    val medio = if (externos) lim(vh * 0.21f, 60f, 88f) else lim(vh * 0.24f, 66f, 98f)
    val pequeno = lim(vh * 0.175f, 52f, 72f)
    val gap = lim(vh * 0.032f, 10f, 16f)
    val pad = lim(vh * 0.05f, 14f, 26f)
    val ox = zw - pad - grande / 2f
    val oy = zh - pad - grande / 2f
    val anel1 = grande / 2f + medio / 2f + gap
    val anel2 = anel1 + medio / 2f + pequeno / 2f + gap * 0.6f
    return defs.map { d ->
        var tam = when (d.pos) {
            "main" -> grande
            "ww", "nn" -> pequeno
            else -> medio
        }
        var x = ox
        var y = oy
        if (d.pos != "main") {
            val a = Math.toRadians(ANGULOS[d.pos] ?: 180.0)
            val r = if (d.pos == "ww" || d.pos == "nn") anel2 else anel1
            x = ox + (cos(a) * r).toFloat()
            y = oy - (sin(a) * r).toFloat()
        }
        if (hud.canhoto) x = zw - x
        val meu = hud.botoes[d.acao]
        if (meu != null) {
            tam = lim(tam * meu.s, 40f, 200f)
            if (meu.x != null && meu.y != null) {
                x = lim(meu.x * zw, tam / 2f, zw - tam / 2f)
                y = lim(meu.y * zh, tam / 2f, zh - tam / 2f)
            }
        }
        PosBotao(d, zona.left + x * k, zona.top + y * k, tam * k)
    }
}

/** "MARTELO DO TROVÃO ETERNO" cabe embaixo do botão como "MARTELO DO" (até 14 letras, sem terminar em DE/DA...). */
fun nomeCurto(nome: String): String {
    if (nome.length <= 14) return nome
    var out = ""
    for (w in nome.split(" ")) {
        if ((if (out.isEmpty()) 0 else out.length + 1) + w.length > 14) break
        out = if (out.isEmpty()) w else "$out $w"
    }
    val palavras = (out.ifEmpty { nome.take(14) }).split(" ").toMutableList()
    while (palavras.size > 1 && palavras.last() in setOf("DE", "DA", "DO", "DAS", "DOS", "E")) palavras.removeAt(palavras.size - 1)
    return palavras.joinToString(" ")
}
