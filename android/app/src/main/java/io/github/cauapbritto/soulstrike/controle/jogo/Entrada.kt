package io.github.cauapbritto.soulstrike.controle.jogo

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlin.random.Random

/**
 * O estado completo do controle, como o site manda: botões segurados, analógico e quantas vezes
 * cada botão foi apertado, tudo com um número de sequência. Pedido atrasado ou perdido na rede não
 * deixa botão preso e nenhum toque rápido se perde (o jogo confere os contadores).
 */
class Entrada {
    private val segurados = LinkedHashSet<String>()
    private val contagem = HashMap<String, Int>()
    private var x = 0f
    private var y = 0f
    private var seq = 0
    var sessao: String = novaSessao()
        private set

    /** Chamado quando algo muda (o canal manda o estado na hora). */
    var aoMudar: (() -> Unit)? = null

    @Synchronized
    fun apertar(acao: String) {
        if (!segurados.add(acao)) return
        contagem[acao] = (contagem[acao] ?: 0) + 1
        aoMudar?.invoke()
    }

    @Synchronized
    fun soltar(acao: String) {
        if (!segurados.remove(acao)) return
        aoMudar?.invoke()
    }

    /** Um aperto só (botão de menu): conta sem ficar segurado. */
    @Synchronized
    fun tocar(acao: String) {
        contagem[acao] = (contagem[acao] ?: 0) + 1
        aoMudar?.invoke()
    }

    /** Analógico de -1 a 1. Só avisa quando muda de verdade (ou volta ao centro). */
    @Synchronized
    fun eixo(nx: Float, ny: Float): Boolean {
        val mudou = abs(nx - x) + abs(ny - y) > 0.04f || (nx == 0f && ny == 0f && (x != 0f || y != 0f))
        x = nx
        y = ny
        if (mudou) aoMudar?.invoke()
        return mudou
    }

    @Synchronized
    fun soltarTudo() {
        val tinha = segurados.isNotEmpty() || x != 0f || y != 0f
        segurados.clear()
        x = 0f
        y = 0f
        if (tinha) aoMudar?.invoke()
    }

    /** Página nova para o jogo (ao conectar de novo): recomeça a contagem dos dois lados. */
    @Synchronized
    fun novaConexao() {
        segurados.clear()
        contagem.clear()
        x = 0f
        y = 0f
        seq = 0
        sessao = novaSessao()
    }

    @get:Synchronized
    val ativo: Boolean
        get() = segurados.isNotEmpty() || x != 0f || y != 0f

    @Synchronized
    fun segurando(acao: String): Boolean = acao in segurados

    /** O pacote do estado atual (o mesmo do /api/input, com o tipo "in" do canal rápido). */
    @Synchronized
    fun pacote(vaga: Int, token: String, tm: Long? = null): JSONObject {
        seq += 1
        val o = JSONObject()
        o.put("t", "in")
        o.put("slot", vaga)
        o.put("token", token)
        o.put("sid", sessao)
        o.put("seq", seq)
        o.put("held", JSONArray(segurados.toList()))
        val c = JSONObject()
        for ((k, v) in contagem) c.put(k, v)
        o.put("counts", c)
        o.put("x", (x * 100f).roundToInt() / 100.0)
        o.put("y", (y * 100f).roundToInt() / 100.0)
        if (tm != null) o.put("tm", tm)
        return o
    }

    private fun novaSessao(): String = "app" + Random.nextLong(1L shl 40).toString(36)
}
