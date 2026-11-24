package io.github.cauapbritto.soulstrike.controle.rede

import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import io.github.cauapbritto.soulstrike.controle.JogoSalvo
import io.github.cauapbritto.soulstrike.controle.Prefs
import io.github.cauapbritto.soulstrike.controle.jogo.Caderno
import io.github.cauapbritto.soulstrike.controle.jogo.Entrada
import io.github.cauapbritto.soulstrike.controle.jogo.Heroi
import io.github.cauapbritto.soulstrike.controle.jogo.MapaJogo
import io.github.cauapbritto.soulstrike.controle.jogo.Rapido
import io.github.cauapbritto.soulstrike.controle.jogo.Status
import io.github.cauapbritto.soulstrike.controle.jogo.limparApelido
import io.github.cauapbritto.soulstrike.controle.jogo.objetos
import io.github.cauapbritto.soulstrike.controle.ui.Imagens
import io.github.cauapbritto.soulstrike.controle.vibra.Vibrador
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.util.concurrent.Executors
import kotlin.concurrent.thread

enum class Estado { FORA, CONECTANDO, VAGA, OK, CAIU }

/**
 * A conversa com o jogo. O estado do controle vai pelo canal rápido (UDP na porta do jogo) e
 * volta um pulso com vibração, fôlego, munição e energia. O resto (seleção, loja, novidades) vem
 * pelo /api/status, só quando muda. Se o UDP não passar (firewall antigo, jogo velho), tudo vai
 * por HTTP, igual ao site, sem o jogador perceber.
 */
class Canal(private val prefs: Prefs, private val vibrador: Vibrador) {
    var estado by mutableStateOf(Estado.FORA)
        private set
    var endereco by mutableStateOf<Endereco?>(null)
        private set
    var nomePc by mutableStateOf("")
        private set
    var versaoJogo by mutableStateOf("")
        private set
    var status by mutableStateOf<Status?>(null)
        private set
    var rapido by mutableStateOf(Rapido())
        private set
    var rtt by mutableIntStateOf(-1)
        private set
    var udpVivo by mutableStateOf(false)
        private set
    var udpNoJogo by mutableStateOf(false)
        private set
    var tentativas by mutableIntStateOf(0)
        private set
    var caiuEm by mutableStateOf(0L)
        private set
    var erro by mutableStateOf<String?>(null)
    var aviso by mutableStateOf<String?>(null)
    var roster by mutableStateOf<List<Heroi>>(emptyList())
        private set
    var vaga by mutableIntStateOf(0)
        private set

    val entrada = Entrada()
    val token: String get() = prefs.token

    /** Entrou numa vaga: o app guarda o jogo (o atalho VOLTAR AO... do ícone usa). */
    var aoLembrar: ((JogoSalvo) -> Unit)? = null

    private val main = Handler(Looper.getMainLooper())
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val envioUdp = Executors.newSingleThreadExecutor()
    private val envioHttp = Executors.newSingleThreadExecutor()
    private var trabalhos = mutableListOf<Job>()
    private val pedidoStatus = Channel<Unit>(Channel.CONFLATED)

    @Volatile private var sock: DatagramSocket? = null
    @Volatile private var base = ""
    @Volatile private var vagaAtual = 0
    @Volatile private var ultimaResposta = 0L
    @Volatile private var ultimoPulso = 0L
    @Volatile private var pausado = false
    @Volatile private var statusVisto = -1L
    @Volatile private var statusPedido = -2L
    @Volatile private var httpIndo = false
    @Volatile private var httpPendente = false
    @Volatile private var maiorVibra = -1
    @Volatile private var rosterTam = -1
    @Volatile private var geracao = 0
    @Volatile private var semApelido = false
    @Volatile private var apelidoEm = 0L
    @Volatile private var reacaoEm = 0L

    init {
        entrada.aoMudar = { enviar() }
    }

    // ── conectar e sair ───────────────────────

    /** Conecta no jogo deste endereço. Com vaga (do QR), já entra nela; sem, mostra a escolha. */
    fun conectar(end: Endereco) {
        desligar(sairDaVaga = true)
        val minha = ++geracao
        erro = null
        aviso = null
        endereco = end
        estado = Estado.CONECTANDO
        status = null
        rapido = Rapido()
        rtt = -1
        semApelido = false
        apelidoEm = 0L
        escopo.launch {
            val b = end.base
            val app = Http.get("$b/api/app", 2500)
            var nome = end.host
            var versao = ""
            var udp = false
            if (app != null && app.ok) {
                val o = app.json()
                if (o != null && o.optString("jogo") == "soulstrike") {
                    nome = o.optString("nome").ifEmpty { end.host }
                    versao = o.optString("versao")
                    udp = o.optBoolean("udp")
                }
            } else {
                // jogo antigo (sem /api/app) ainda funciona pelo jeito do site
                val st = Http.get("$b/api/status?slot=0&token=${prefs.token}", 2500)
                if (st == null || !st.ok || st.json()?.has("phase") != true) {
                    noMain(minha) {
                        erro = "NÃO ACHEI O JOGO EM ${end.host}. O JOGO ESTÁ ABERTO NA MESMA WI-FI?"
                        estado = Estado.FORA
                        endereco = null
                    }
                    return@launch
                }
                aviso = "JOGO ANTIGO: ATUALIZE O JOGO PARA O CANAL RÁPIDO"
            }
            base = b
            Imagens.base = b
            noMain(minha) {
                nomePc = nome
                versaoJogo = versao
                udpNoJogo = udp
            }
            carregarRoster()
            abrirUdp(end, minha)
            iniciarLaços(minha)
            if (end.vaga in 1..4) entrarNaVaga(end.vaga, minha, avisarOcupada = true)
            else noMain(minha) { estado = Estado.VAGA }
        }
    }

    /** Escolheu (ou trocou) a vaga na tela de vagas. */
    fun escolherVaga(n: Int) {
        val minha = geracao
        escopo.launch { entrarNaVaga(n, minha, avisarOcupada = true) }
    }

    /** "trocar de jogador": sai da vaga e volta para a escolha, ainda conectado ao jogo. */
    fun trocarVaga() {
        val v = vagaAtual
        entrada.soltarTudo()
        vagaAtual = 0
        vaga = 0
        estado = Estado.VAGA
        if (v != 0) {
            val b = base
            escopo.launch { Http.post("$b/api/leave", JSONObject().put("slot", v).put("token", prefs.token)) }
        }
        pedirStatus()
    }

    /** Sai do jogo de vez (volta ao menu de conexão). */
    fun sair() {
        desligar(sairDaVaga = true)
        geracao++
        estado = Estado.FORA
        endereco = null
        status = null
        vaga = 0
    }

    /** O botão TENTAR AGORA da tela de conexão caída. */
    fun tentarAgora() {
        tentativas += 1
        pedirStatus()
        enviar()
    }

    /** O app foi para o fundo: solta tudo e para de mandar. */
    fun pausar() {
        entrada.soltarTudo()
        enviar()
        pausado = true
    }

    fun retomar() {
        pausado = false
        if (estado == Estado.OK || estado == Estado.CAIU || estado == Estado.VAGA) {
            ultimaResposta = SystemClock.elapsedRealtime()
            pedirStatus()
        }
    }

    private suspend fun entrarNaVaga(n: Int, minha: Int, avisarOcupada: Boolean) {
        val r = Http.post("$base/api/join", JSONObject().put("slot", n).put("token", prefs.token))
        if (minha != geracao) return
        if (r != null && r.ok) {
            entrada.novaConexao()
            vagaAtual = n
            maiorVibra = -1
            ultimaResposta = SystemClock.elapsedRealtime()
            noMain(minha) {
                vaga = n
                erro = null
                estado = Estado.OK
                tentativas = 0
                val end = endereco
                if (end != null) {
                    val jogo = JogoSalvo(end.host, end.porta, nomePc, n, System.currentTimeMillis())
                    prefs.lembrar(jogo)
                    aoLembrar?.invoke(jogo)
                }
            }
            pedirStatus()
            enviar()
        } else {
            noMain(minha) {
                if (r == null) erro = "O JOGO NÃO RESPONDEU. TENTE DE NOVO."
                else if (avisarOcupada) erro = "O JOGADOR $n JÁ ESTÁ EM USO. ESCOLHA OUTRO."
                estado = Estado.VAGA
            }
        }
    }

    private fun desligar(sairDaVaga: Boolean) {
        val v = vagaAtual
        val b = base
        for (t in trabalhos) t.cancel()
        trabalhos.clear()
        entrada.soltarTudo()
        if (sairDaVaga && v != 0 && b.isNotEmpty()) {
            escopo.launch { Http.post("$b/api/leave", JSONObject().put("slot", v).put("token", prefs.token)) }
        }
        vagaAtual = 0
        val s = sock
        sock = null
        if (s != null) envioUdp.execute { try { s.close() } catch (e: Exception) { } }
        udpVivo = false
        ultimoPulso = 0L
        statusVisto = -1L
        statusPedido = -2L
    }

    // ── laços: status, pulso, vigia ────────────

    private fun iniciarLaços(minha: Int) {
        ultimaResposta = SystemClock.elapsedRealtime()
        trabalhos += escopo.launch {
            while (isActive && minha == geracao) {
                val espera = when {
                    estado == Estado.CAIU -> 900L
                    udpVivoAgora() -> 2000L
                    else -> 400L
                }
                withTimeoutOrNull(espera) { pedidoStatus.receive() }
                if (!pausado) buscarStatus(minha)
            }
        }
        trabalhos += escopo.launch {
            while (isActive && minha == geracao) {
                delay(100)
                if (pausado || vagaAtual == 0) continue
                val vivo = udpVivoAgora()
                if (sock != null) mandarUdp()
                if (!vivo && entrada.ativo) mandarHttp()
                if (vivo != udpVivo) noMain(minha) { udpVivo = vivo }
            }
        }
        trabalhos += escopo.launch {
            while (isActive && minha == geracao) {
                delay(500)
                if (pausado) continue
                val parado = SystemClock.elapsedRealtime() - ultimaResposta
                val e = estado
                if ((e == Estado.OK || e == Estado.VAGA) && parado > 3000) {
                    entrada.soltarTudo()
                    noMain(minha) {
                        estado = Estado.CAIU
                        caiuEm = SystemClock.elapsedRealtime()
                        tentativas = 1
                        vibrador.tocar("caiu")
                    }
                } else if (e == Estado.CAIU) {
                    val n = 1 + ((SystemClock.elapsedRealtime() - caiuEm) / 3000L).toInt()
                    if (n != tentativas) noMain(minha) { tentativas = n }
                }
            }
        }
    }

    private fun udpVivoAgora(): Boolean = SystemClock.elapsedRealtime() - ultimoPulso < 1500

    fun pedirStatus() {
        pedidoStatus.trySend(Unit)
    }

    private suspend fun buscarStatus(minha: Int) {
        val b = base
        if (b.isEmpty()) return
        val v = vagaAtual
        val r = Http.get("$b/api/status?slot=$v&token=${prefs.token}", 2500) ?: return
        val o = r.json() ?: return
        if (minha != geracao) return
        val s = try { Status(o) } catch (e: Exception) { return }
        respondeu()
        statusVisto = statusPedido
        val me = s.me
        if (!udpVivoAgora() && me != null) vibrarSe(me.rapido.vibra, me.rapido.vibraPadrao)
        if (s.roster > 0 && s.roster != rosterTam) carregarRoster()
        noMain(minha) {
            status = s
            if (!udpVivoAgora() && me != null) rapido = me.rapido
            if (estado == Estado.CAIU) {
                estado = if (vagaAtual == 0) Estado.VAGA else Estado.OK
                tentativas = 0
            }
        }
        // a vaga se perdeu (jogo reaberto ou 20 s fora): entra de novo sozinho
        if (v != 0 && me != null && !me.dono) entrarNaVaga(v, minha, avisarOcupada = false)
        // o apelido da TV: o jogo esquece quando reabre ou a vaga cai, então o app manda de novo
        if (v != 0 && me != null && me.dono && s.temExtras && !semApelido) {
            val quero = limparApelido(prefs.apelido).ifEmpty { null }
            if (quero != me.apelido && SystemClock.elapsedRealtime() - apelidoEm > 5000L) mandarApelido()
        }
    }

    private fun respondeu() {
        ultimaResposta = SystemClock.elapsedRealtime()
    }

    private suspend fun carregarRoster() {
        val r = Http.get("$base/api/roster", 4000) ?: return
        val arr = r.jsonLista() ?: return
        val lista = arr.objetos().map { Heroi(it) }
        rosterTam = lista.size
        val minha = geracao
        noMain(minha) { roster = lista }
    }

    // ── canal rápido (UDP) ─────────────────────

    private fun abrirUdp(end: Endereco, minha: Int) {
        val s = try {
            DatagramSocket().apply {
                soTimeout = 400
                connect(InetAddress.getByName(end.host), end.porta)
            }
        } catch (e: Exception) {
            null
        } ?: return
        sock = s
        thread(name = "canal-rapido", isDaemon = true) { ouvir(s, minha) }
    }

    private fun ouvir(s: DatagramSocket, minha: Int) {
        val buf = ByteArray(8192)
        while (sock === s && minha == geracao) {
            try {
                val pkt = DatagramPacket(buf, buf.size)
                s.receive(pkt)
                val o = JSONObject(String(pkt.data, 0, pkt.length, Charsets.UTF_8))
                when (o.optString("t")) {
                    "p" -> pulso(o, minha)
                    "nao" -> if (o.optInt("code") == 403) pedirStatus()
                }
            } catch (e: java.net.SocketTimeoutException) {
                // nada chegou: confere se o canal ainda é este
            } catch (e: Exception) {
                if (sock !== s) return
                try { Thread.sleep(50) } catch (i: InterruptedException) { return }
            }
        }
    }

    private fun pulso(o: JSONObject, minha: Int) {
        val agora = SystemClock.elapsedRealtime()
        ultimoPulso = agora
        respondeu()
        val tm = o.optLong("tm", 0L)
        val ida = if (tm > 0L) (agora - tm).toInt().coerceIn(0, 5000) else -1
        val st = o.optLong("st", -1L)
        if (st != -1L && st != statusVisto && st != statusPedido) {
            statusPedido = st
            pedirStatus()
        }
        val me = o.optJSONObject("me")
        val r = Rapido.de(me)
        vibrarSe(r.vibra, r.vibraPadrao)
        noMain(minha) {
            rapido = r
            if (!udpVivo) udpVivo = true
            if (ida >= 0) rtt = if (rtt < 0) ida else (rtt * 0.8f + ida * 0.2f).toInt()
            if (estado == Estado.CAIU) {
                estado = if (vagaAtual == 0) Estado.VAGA else Estado.OK
                tentativas = 0
            }
        }
    }

    // ── mandar o controle ─────────────────────

    /** O estado do controle mudou: manda na hora (UDP e, sem ele, HTTP). */
    private fun enviar() {
        if (vagaAtual == 0) return
        if (sock != null) mandarUdp()
        if (!udpVivoAgora()) mandarHttp()
    }

    private fun mandarUdp() {
        val s = sock ?: return
        val v = vagaAtual
        if (v == 0) return
        val dados = entrada.pacote(v, prefs.token, SystemClock.elapsedRealtime()).toString().toByteArray(Charsets.UTF_8)
        envioUdp.execute {
            try {
                s.send(DatagramPacket(dados, dados.size))
            } catch (e: Exception) {
                // rede caiu: o vigia avisa
            }
        }
    }

    private fun mandarHttp() {
        if (httpIndo) {
            httpPendente = true
            return
        }
        httpIndo = true
        envioHttp.execute {
            var de_novo = true
            while (de_novo) {
                httpPendente = false
                val v = vagaAtual
                val b = base
                if (v == 0 || b.isEmpty()) break
                val t0 = SystemClock.elapsedRealtime()
                val r = Http.post("$b/api/input", entrada.pacote(v, prefs.token), 1500)
                if (r != null && (r.ok || r.codigo == 204)) {
                    respondeu()
                    val ms = (SystemClock.elapsedRealtime() - t0).toInt()
                    if (!udpVivoAgora()) main.post { rtt = if (rtt < 0) ms else (rtt * 0.8f + ms * 0.2f).toInt() }
                }
                de_novo = httpPendente
            }
            httpIndo = false
        }
    }

    // ── loja, novidades, computador ───────────

    /** Loja do celular: marcar (comprar = false) ou comprar um item; "fechar", "voltar", "pc:...". */
    fun pedirLoja(item: String, comprar: Boolean) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return
        escopo.launch {
            Http.post("$b/api/shop", JSONObject().put("slot", v).put("token", prefs.token).put("item", item).put("buy", comprar))
            delay(90)
            pedirStatus()
        }
    }

    /** Tela de novidades: "prev", "next" ou "skip". */
    fun novidade(go: String) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return
        escopo.launch {
            Http.post("$b/api/news", JSONObject().put("slot", v).put("token", prefs.token).put("go", go))
            delay(90)
            pedirStatus()
        }
    }

    // ── apelido, reações, mapa e caderno ──────

    /** Manda o apelido guardado no celular (vazio volta ao P1). */
    fun mandarApelido() {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return
        apelidoEm = SystemClock.elapsedRealtime()
        val nick = limparApelido(prefs.apelido)
        val minha = geracao
        escopo.launch {
            val r = Http.post("$b/api/nick", JSONObject().put("slot", v).put("token", prefs.token).put("nick", nick))
            if (r != null && (r.codigo == 404 || r.codigo == 405)) semApelido = true      // jogo antigo
            if (minha == geracao) pedirStatus()
        }
    }

    /** Reação rápida (gg, kkk, vem, palmas): o balão aparece em cima do boneco na TV. */
    fun reagir(tipo: String) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return
        val agora = SystemClock.elapsedRealtime()
        if (agora - reacaoEm < 1000L) return               // o jogo aceita uma por segundo
        reacaoEm = agora
        val minha = geracao
        escopo.launch {
            val r = Http.post("$b/api/reacao", JSONObject().put("slot", v).put("token", prefs.token).put("kind", tipo))
            if (r != null && (r.codigo == 404 || r.codigo == 405)) {
                noMain(minha) { aviso = "ESTE JOGO AINDA NÃO TEM REAÇÕES: ATUALIZE O JOGO" }
            }
        }
    }

    /** Frase para a equipe (passa, chuta, ajuda, frente, cuidado, aqui): só os colegas de time recebem. */
    fun chamarEquipe(tipo: String) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return
        val agora = SystemClock.elapsedRealtime()
        if (agora - reacaoEm < 1000L) return               // a mesma regra das reações: uma por segundo
        reacaoEm = agora
        val minha = geracao
        escopo.launch {
            val r = Http.post("$b/api/equipe", JSONObject().put("slot", v).put("token", prefs.token).put("kind", tipo))
            if (r != null && (r.codigo == 404 || r.codigo == 405)) {
                noMain(minha) { aviso = "ESTE JOGO AINDA NÃO TEM O BOTÃO EQUIPE: ATUALIZE O JOGO" }
            }
        }
    }

    /** O MAPA da partida (fase ou Casa) agora, ou null (sem mapa, jogo antigo ou rede ruim). */
    suspend fun buscarMapa(): MapaJogo? = withContext(Dispatchers.IO) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return@withContext null
        val o = Http.get("$b/api/mapa?slot=$v&token=${prefs.token}", 2000)?.json()?.optJSONObject("map")
            ?: return@withContext null
        try { MapaJogo(o) } catch (e: Exception) { null }
    }

    /** O CADERNO DE SEGREDOS do jogo, ou null. */
    suspend fun buscarCaderno(): Caderno? = withContext(Dispatchers.IO) {
        val v = vagaAtual
        val b = base
        if (v == 0 || b.isEmpty()) return@withContext null
        val r = Http.get("$b/api/caderno?slot=$v&token=${prefs.token}", 3000)
        val o = if (r != null && r.ok) r.json() else null
        if (o == null) null else try { Caderno(o) } catch (e: Exception) { null }
    }

    /** Endereço da cópia da tela do computador da Casa (muda a cada versão). */
    fun urlTela(versao: Int): String =
        "$base/api/tela.png?slot=$vagaAtual&token=${prefs.token}&v=${versao}_${SystemClock.elapsedRealtime()}"

    // ── vibração do jogo ──────────────────────

    private fun vibrarSe(n: Int, padrao: String) {
        if (n < 0) return
        val antes = maiorVibra
        if (antes < 0 || n < antes - 50) {          // primeira notícia (ou jogo reaberto): não vibra pelo passado
            maiorVibra = n
            return
        }
        if (n > antes) {
            maiorVibra = n
            main.post { vibrador.tocar(padrao) }
        }
    }

    private fun noMain(minha: Int, bloco: () -> Unit) {
        main.post { if (minha == geracao) bloco() }
    }
}
