package io.github.cauapbritto.soulstrike.controle

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.security.SecureRandom

/** Um jogo em que o celular já entrou (aparece em VOLTAR AO ... e nos RECENTES). */
data class JogoSalvo(val host: String, val porta: Int, val nome: String, val vaga: Int, val quando: Long)

/** O que fica guardado no celular: identidade, últimos jogos, vibração e o jeito dos botões. */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("soulstrike", Context.MODE_PRIVATE)

    /** Identidade do celular para o jogo (a vaga fica guardada para ele quando a Wi-Fi cai). */
    val token: String = sp.getString("token", null) ?: novoToken().also { sp.edit().putString("token", it).apply() }

    /** 0 = desligada, 1 = fraca, 2 = média, 3 = forte. */
    var vibracao: Int
        get() = sp.getInt("vibracao", 2).coerceIn(0, 3)
        set(v) = sp.edit().putInt("vibracao", v.coerceIn(0, 3)).apply()

    /** Um toquinho de vibração a cada botão apertado. */
    var cliqueAoTocar: Boolean
        get() = sp.getBoolean("clique", true)
        set(v) = sp.edit().putBoolean("clique", v).apply()

    /** O apelido que a TV mostra no lugar de P1 (vazio = P1). */
    var apelido: String
        get() = sp.getString("apelido", "") ?: ""
        set(v) = sp.edit().putString("apelido", v).apply()

    /** Últimos jogos (o mais recente primeiro), no máximo 4. */
    fun recentes(): List<JogoSalvo> {
        val raw = sp.getString("recentes", null) ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length()).mapNotNull { i ->
                val o = arr.optJSONObject(i) ?: return@mapNotNull null
                val host = o.optString("host")
                if (host.isEmpty()) null
                else JogoSalvo(host, o.optInt("porta", 5000), o.optString("nome"), o.optInt("vaga", 1), o.optLong("quando"))
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun lembrar(jogo: JogoSalvo) {
        val lista = listOf(jogo) + recentes().filter { it.host != jogo.host || it.porta != jogo.porta }
        val arr = JSONArray()
        for (j in lista.take(4)) {
            arr.put(JSONObject().put("host", j.host).put("porta", j.porta).put("nome", j.nome)
                .put("vaga", j.vaga).put("quando", j.quando))
        }
        sp.edit().putString("recentes", arr.toString()).apply()
    }

    fun esquecerRecentes() = sp.edit().remove("recentes").apply()

    /** Ajustes do controle de um perfil (campanha, duelo, futebol, basquete, luta), em JSON. */
    fun hud(perfil: String): String? = sp.getString("hud_$perfil", null)

    fun salvarHud(perfil: String, json: String?) {
        if (json == null) sp.edit().remove("hud_$perfil").apply() else sp.edit().putString("hud_$perfil", json).apply()
    }

    private fun novoToken(): String {
        val r = SecureRandom()
        val letras = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "app" + (1..20).map { letras[r.nextInt(letras.length)] }.joinToString("")
    }
}
