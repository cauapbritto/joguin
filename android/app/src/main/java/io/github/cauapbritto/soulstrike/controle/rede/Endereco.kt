package io.github.cauapbritto.soulstrike.controle.rede

import android.net.Uri

/** Onde o jogo está: o computador na Wi-Fi, a porta (5000) e a vaga que o QR mandou (0 = escolher). */
data class Endereco(val host: String, val porta: Int = PORTA, val vaga: Int = 0) {
    val base: String get() = "http://$host:$porta"

    companion object {
        const val PORTA = 5000

        /** O link do QR da TV: http://192.168.0.10:5000/?player=2 (ou só o endereço digitado). */
        fun ler(texto: String): Endereco? {
            val t = texto.trim()
            if (t.isEmpty()) return null
            if (t.startsWith("http://", ignoreCase = true) || t.startsWith("https://", ignoreCase = true)) {
                return try {
                    val u = Uri.parse(t)
                    val host = u.host ?: return null
                    if (!hostValido(host)) return null
                    val porta = if (u.port in 1..65535) u.port else PORTA
                    val vaga = u.getQueryParameter("player")?.toIntOrNull()?.takeIf { it in 1..4 } ?: 0
                    Endereco(host, porta, vaga)
                } catch (e: Exception) {
                    null
                }
            }
            // digitado: 192.168.0.10 ou 192.168.0.10:5000
            val partes = t.split(":")
            if (partes.size > 2) return null
            val host = partes[0]
            if (!hostValido(host)) return null
            val porta = if (partes.size == 2) partes[1].toIntOrNull()?.takeIf { it in 1..65535 } ?: return null else PORTA
            return Endereco(host, porta, 0)
        }

        /** IPv4 completo (o que o QR e a TV mostram) ou um nome simples de computador. */
        fun hostValido(host: String): Boolean {
            if (host.isEmpty() || host.length > 63) return false
            val numeros = host.split(".")
            if (numeros.size == 4 && numeros.all { it.isNotEmpty() && it.length <= 3 && it.all(Char::isDigit) }) {
                return numeros.all { (it.toIntOrNull() ?: 999) <= 255 }
            }
            return host.all { it.isLetterOrDigit() || it == '-' || it == '.' } && host.any { it.isLetter() }
        }

        /** O jogo só fala com a rede de casa: IP de rede local (o celular nunca sai para a internet). */
        fun redeLocal(host: String): Boolean {
            val n = host.split(".").mapNotNull { it.toIntOrNull() }
            if (n.size != 4) return true          // nome de computador: deixa tentar
            return n[0] == 10 || n[0] == 127 || (n[0] == 192 && n[1] == 168) || (n[0] == 172 && n[1] in 16..31) ||
                (n[0] == 169 && n[1] == 254) || (n[0] == 100 && n[1] in 64..127)
        }
    }
}
