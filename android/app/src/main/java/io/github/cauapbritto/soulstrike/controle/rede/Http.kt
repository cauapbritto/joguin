package io.github.cauapbritto.soulstrike.controle.rede

import org.json.JSONArray
import org.json.JSONObject
import android.net.Network
import java.io.ByteArrayOutputStream
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.HttpURLConnection
import java.net.URL

/** HTTP pequeno e direto (o jogo fala HTTP/1.1 com conexão mantida, como o site). */
object Http {
    class Resposta(val codigo: Int, val corpo: ByteArray) {
        val ok: Boolean get() = codigo in 200..299
        fun texto(): String = String(corpo, Charsets.UTF_8)
        fun json(): JSONObject? = try { JSONObject(texto()) } catch (e: Exception) { null }
        fun jsonLista(): JSONArray? = try { JSONArray(texto()) } catch (e: Exception) { null }
    }

    fun get(url: String, tempo: Int = 2500): Resposta? = pedir("GET", url, null, tempo)

    /**
     * GET que diz o porquê quando falha (vai em ``motivos``) e pode ir por uma rede escolhida
     * (``rede``: a Wi-Fi, mesmo quando o Android prefere os dados móveis).
     */
    fun sondar(url: String, tempo: Int, rede: Network? = null, motivos: MutableList<String>? = null): Resposta? =
        pedir("GET", url, null, tempo, rede, motivos)

    fun post(url: String, corpo: JSONObject?, tempo: Int = 2500): Resposta? =
        pedir("POST", url, corpo?.toString()?.toByteArray(Charsets.UTF_8), tempo)

    // sem disconnect(): lida a resposta inteira, a conexão volta para o "pool" e o próximo pedido reaproveita
    private fun pedir(
        metodo: String,
        url: String,
        corpo: ByteArray?,
        tempo: Int,
        rede: Network? = null,
        motivos: MutableList<String>? = null,
    ): Resposta? {
        return try {
            val u = URL(url)
            val con = (if (rede != null) rede.openConnection(u) else u.openConnection()) as HttpURLConnection
            con.requestMethod = metodo
            con.connectTimeout = tempo
            con.readTimeout = tempo
            con.useCaches = false
            con.setRequestProperty("Cache-Control", "no-store")
            if (corpo != null) {
                con.doOutput = true
                con.setRequestProperty("Content-Type", "application/json")
                con.setFixedLengthStreamingMode(corpo.size)
                con.outputStream.use { it.write(corpo) }
            }
            val codigo = con.responseCode
            val entrada = if (codigo >= 400) con.errorStream else con.inputStream
            val bytes = entrada?.use { s ->
                val out = ByteArrayOutputStream()
                val buf = ByteArray(8192)
                while (true) {
                    val n = s.read(buf)
                    if (n < 0) break
                    out.write(buf, 0, n)
                    if (out.size() > 4 * 1024 * 1024) break
                }
                out.toByteArray()
            } ?: ByteArray(0)
            Resposta(codigo, bytes)
        } catch (e: Exception) {
            motivos?.add(motivo(e))
            null
        }
    }

    /** O erro do Android em palavras de gente (aparece na tela quando não acha o jogo). */
    fun motivo(e: Throwable): String {
        val m = (e.message ?: "").uppercase()
        return when {
            e is SocketTimeoutException -> "O COMPUTADOR NÃO RESPONDEU A TEMPO"
            "EPERM" in m || "EACCES" in m || e is SecurityException -> "O ANDROID BLOQUEOU O APP (PERMISSÃO DE REDE LOCAL)"
            "ECONNREFUSED" in m -> "O COMPUTADOR RECUSOU (JOGO FECHADO OU OUTRA PORTA)"
            "ENETUNREACH" in m || "EHOSTUNREACH" in m || "ENONET" in m -> "O CELULAR NÃO ALCANÇA ESSA REDE"
            e is ConnectException -> "NÃO CONECTOU (${m.take(50)})"
            else -> "${e.javaClass.simpleName.uppercase()} ${m.take(50)}".trim()
        }
    }
}
