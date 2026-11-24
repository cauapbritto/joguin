package io.github.cauapbritto.soulstrike.controle.rede

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import io.github.cauapbritto.soulstrike.controle.jogo.VagaInfo
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.Inet4Address
import java.net.InetAddress
import java.net.SocketTimeoutException

/** Um jogo aberto que respondeu na Wi-Fi. */
data class JogoAchado(
    val host: String,
    val porta: Int,
    val nome: String,
    val versao: String,
    val protocolo: Int,
    val fase: String,
    val modo: String,
    val vagas: Map<Int, VagaInfo>,
    val ms: Int,
)

/**
 * PROCURAR: pergunta "tem jogo aí?" para a rede inteira (broadcast na porta do jogo) e junta quem
 * responde. A pergunta vai "acolchoada" (maior que a resposta), como o jogo exige.
 *
 * Se ninguém responder (firewall que só libera o TCP, roteador que barra broadcast), o app bate
 * na porta 5000 de cada endereço da faixa da Wi-Fi (o mesmo caminho do DIGITAR, que funciona).
 */
class Descoberta(context: Context) {
    var jogos by mutableStateOf<List<JogoAchado>>(emptyList())
        private set
    var procurando by mutableStateOf(false)
        private set

    private val app = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var trabalho: Job? = null
    private var rodada = 0

    /** Os endereços dos jogos salvos (VOLTAR AO... e DIGITAR): a procura confere eles também. */
    var recentes: () -> List<String> = { emptyList() }

    /** Computadores que a varredura achou (a próxima procura confere eles primeiro). */
    @Volatile private var conhecidos: List<String> = emptyList()

    /** Procura por uns segundos (várias perguntas seguidas: um pacote perdido não esconde o jogo). */
    fun procurar(rodadas: Int = 5) {
        trabalho?.cancel()
        val minha = ++rodada
        procurando = true
        trabalho = escopo.launch {
            val achados = LinkedHashMap<String, JogoAchado>()
            val sock = try {
                DatagramSocket().apply {
                    broadcast = true
                    soTimeout = 200
                }
            } catch (e: Exception) {
                null
            }
            if (sock == null) {
                main.post { if (minha == rodada) procurando = false }
                return@launch
            }
            try {
                val pergunta = JSONObject()
                    .put("t", "oi")
                    .put("v", 1)
                    .put("app", "soulstrike-controle")
                    .put("pad", "x".repeat(300))
                    .toString()
                    .toByteArray(Charsets.UTF_8)
                val destinos = destinos()
                val buf = ByteArray(4096)
                for (r in 0 until rodadas) {
                    if (!isActive) break
                    val t0 = SystemClock.elapsedRealtime()
                    for (d in destinos) {
                        try {
                            sock.send(DatagramPacket(pergunta, pergunta.size, d, Endereco.PORTA))
                        } catch (e: Exception) {
                            // rede sem broadcast: tenta os outros destinos
                        }
                    }
                    val fim = t0 + 800
                    while (isActive && SystemClock.elapsedRealtime() < fim) {
                        try {
                            val p = DatagramPacket(buf, buf.size)
                            sock.receive(p)
                            val j = ler(p, (SystemClock.elapsedRealtime() - t0).toInt()) ?: continue
                            val chave = j.host + ":" + j.porta
                            val antes = achados[chave]
                            achados[chave] = if (antes != null && antes.ms < j.ms) j.copy(ms = antes.ms) else j
                            val lista = achados.values.toList()
                            main.post { if (minha == rodada) jogos = lista }
                        } catch (e: SocketTimeoutException) {
                            // ninguém respondeu agora
                        } catch (e: Exception) {
                            break
                        }
                    }
                    if (achados.isNotEmpty()) break
                    // a primeira pergunta ficou sem resposta: tenta pelo TCP já
                    if (r == 0 && isActive) {
                        val tcp = try {
                            varrer()
                        } catch (e: CancellationException) {
                            throw e
                        } catch (e: Exception) {
                            emptyList()                // a varredura nunca derruba o app
                        }
                        for (j in tcp) achados[j.host + ":" + j.porta] = j
                        if (achados.isNotEmpty()) {
                            val lista = achados.values.toList()
                            main.post { if (minha == rodada) jogos = lista }
                            break
                        }
                    }
                }
            } finally {
                try {
                    sock.close()
                } catch (e: Exception) {
                }
                val lista = achados.values.toList()
                main.post {
                    if (minha == rodada) {
                        jogos = lista
                        procurando = false
                    }
                }
            }
        }
    }

    fun parar() {
        trabalho?.cancel()
        rodada++
        procurando = false
    }

    /** Bate na porta do jogo de cada endereço da faixa do celular (/24), 64 de cada vez. */
    private suspend fun varrer(): List<JogoAchado> {
        // primeiro os computadores já conhecidos (achados antes ou digitados no DIGITAR)
        val salvos = try {
            recentes()
        } catch (e: Exception) {
            emptyList()
        }
        val antes = (conhecidos + salvos).distinct().mapNotNull { perguntarTcp(it) }
        if (antes.isNotEmpty()) {
            conhecidos = antes.map { it.host }
            return antes
        }
        // depois a faixa do celular e a dos jogos salvos (roteador com duas faixas, repetidor...)
        val eu = meuIp()
        val prefixos = (listOfNotNull(eu) + salvos)
            .filter { it.count { c -> c == '.' } == 3 }
            .map { it.substringBeforeLast(".") + "." }
            .distinct()
            .take(3)
        if (prefixos.isEmpty()) return emptyList()
        val hosts = prefixos.flatMap { p -> (1..254).map { p + it } }.filter { it != eu }
        val limite = Semaphore(64)
        val achados = coroutineScope {
            hosts.map { h -> async(Dispatchers.IO) { limite.withPermit { perguntarTcp(h) } } }.awaitAll().filterNotNull()
        }
        conhecidos = achados.map { it.host }
        return achados
    }

    /** /api/app e /api/status de um endereço (null = não é um Soul Strike). */
    private fun perguntarTcp(host: String): JogoAchado? {
        val t0 = SystemClock.elapsedRealtime()
        val base = "http://$host:${Endereco.PORTA}"
        val info = Http.get("$base/api/app", 800)?.takeIf { it.ok }?.json() ?: return null
        if (info.optString("jogo") != "soulstrike") return null
        val ms = (SystemClock.elapsedRealtime() - t0).toInt()
        val st = Http.get("$base/api/status", 1500)?.json()
        val vagas = HashMap<Int, VagaInfo>()
        st?.optJSONObject("slots")?.let { v ->
            for (k in v.keys()) {
                val n = k.toIntOrNull() ?: continue
                val o = v.optJSONObject(k) ?: continue
                vagas[n] = VagaInfo(o.optBoolean("claimed"), o.optBoolean("connected"))
            }
        }
        return JogoAchado(
            host = host,
            porta = info.optInt("porta", Endereco.PORTA),
            nome = info.optString("nome").ifEmpty { host },
            versao = info.optString("versao"),
            protocolo = info.optInt("protocolo", 1),
            fase = st?.optString("phase").orEmpty(),
            modo = st?.optString("mode").orEmpty(),
            vagas = vagas,
            ms = ms,
        )
    }

    /** O IPv4 do celular na Wi-Fi. */
    private fun meuIp(): String? {
        val cm = app.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return null
        return try {
            redesWifi(cm).flatMap { rede -> cm.getLinkProperties(rede)?.linkAddresses.orEmpty() }
                .mapNotNull { it.address as? Inet4Address }
                .firstOrNull { !it.isLoopbackAddress }
                ?.hostAddress
        } catch (e: Exception) {
            null
        }
    }

    private fun ler(p: DatagramPacket, ms: Int): JogoAchado? {
        val o = try {
            JSONObject(String(p.data, 0, p.length, Charsets.UTF_8))
        } catch (e: Exception) {
            return null
        }
        if (o.optString("t") != "jogo" || o.optString("jogo") != "soulstrike") return null
        val host = p.address?.hostAddress ?: return null
        val vagas = HashMap<Int, VagaInfo>()
        val v = o.optJSONObject("vagas")
        if (v != null) {
            for (k in v.keys()) {
                val n = k.toIntOrNull() ?: continue
                val a = v.optJSONArray(k) ?: continue
                vagas[n] = VagaInfo(a.optBoolean(0), a.optBoolean(1))
            }
        }
        return JogoAchado(
            host = host,
            porta = o.optInt("porta", Endereco.PORTA),
            nome = o.optString("nome").ifEmpty { host },
            versao = o.optString("versao"),
            protocolo = o.optInt("v", 1),
            fase = o.optString("fase"),
            modo = o.optString("modo"),
            vagas = vagas,
            ms = ms,
        )
    }

    /** 255.255.255.255 e o broadcast de cada rede IPv4 do celular (alguns roteadores só passam um deles). */
    private fun destinos(): List<InetAddress> {
        val out = ArrayList<InetAddress>()
        try {
            out.add(InetAddress.getByName("255.255.255.255"))
        } catch (e: Exception) {
        }
        val cm = app.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return out
        try {
            for (rede in redesWifi(cm)) {
                val props = cm.getLinkProperties(rede) ?: continue
                for (la in props.linkAddresses) {
                    val ip = la.address as? Inet4Address ?: continue
                    if (ip.isLoopbackAddress) continue
                    val pre = la.prefixLength
                    if (pre !in 8..30) continue
                    val b = ip.address
                    val n = ((b[0].toInt() and 255) shl 24) or ((b[1].toInt() and 255) shl 16) or
                        ((b[2].toInt() and 255) shl 8) or (b[3].toInt() and 255)
                    val mascara = (-1L shl (32 - pre)).toInt()
                    val bc = n or mascara.inv()
                    val bytes = byteArrayOf((bc ushr 24).toByte(), (bc ushr 16).toByte(), (bc ushr 8).toByte(), bc.toByte())
                    val addr = InetAddress.getByAddress(bytes)
                    if (out.none { it == addr }) out.add(addr)
                }
            }
        } catch (e: Exception) {
            // sem acesso às redes: fica só o 255.255.255.255
        }
        return out
    }

    companion object {
        @Suppress("DEPRECATION")
        private fun redesWifi(cm: ConnectivityManager) = cm.allNetworks.filter { rede ->
            val c = cm.getNetworkCapabilities(rede)
            c != null && (c.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) || c.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
        }

        /** O celular está numa Wi-Fi (ou cabo)? */
        fun naWifi(context: Context): Boolean {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
            return try {
                redesWifi(cm).isNotEmpty()
            } catch (e: Exception) {
                false
            }
        }

        /** "192.168.0." da Wi-Fi do celular (o jogo quase sempre está na mesma faixa). */
        fun prefixoDaRede(context: Context): String? {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return null
            return try {
                for (rede in redesWifi(cm)) {
                    val props = cm.getLinkProperties(rede) ?: continue
                    for (la in props.linkAddresses) {
                        val ip = la.address as? Inet4Address ?: continue
                        if (ip.isLoopbackAddress) continue
                        val partes = ip.hostAddress?.split(".") ?: continue
                        if (partes.size == 4) return partes.take(3).joinToString(".") + "."
                    }
                }
                null
            } catch (e: Exception) {
                null
            }
        }

        /**
         * Wi-Fi sem internet faz o Android mandar tudo pelos dados móveis, e aí o jogo (que está na
         * Wi-Fi) some. Nesse caso o app fala só pela Wi-Fi.
         */
        fun prenderNaWifi(context: Context) {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return
            try {
                val ativa = cm.getNetworkCapabilities(cm.activeNetwork)
                val padraoWifi = ativa != null && (ativa.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                    ativa.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
                if (padraoWifi) {
                    if (cm.boundNetworkForProcess != null) cm.bindProcessToNetwork(null)
                    return
                }
                val wifi = redesWifi(cm).firstOrNull()
                if (wifi != null && cm.boundNetworkForProcess != wifi) cm.bindProcessToNetwork(wifi)
            } catch (e: Exception) {
                // sem permissão ou rede sumiu: segue com o padrão do Android
            }
        }
    }
}
