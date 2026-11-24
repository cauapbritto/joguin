package io.github.cauapbritto.soulstrike.controle.atualizar

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.pm.PackageInfoCompat
import io.github.cauapbritto.soulstrike.controle.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * ATUALIZAR: baixa o APK da Release do GitHub (a da versão do jogo) e abre o instalador do Android.
 * Acaba a volta pelo site a cada versão nova. O APK do GitHub sai com a mesma chave deste, então o
 * Android instala por cima, sem desinstalar e sem perder os ajustes.
 */
class Atualizador(context: Context) {
    enum class Fase { PARADO, PROCURANDO, BAIXANDO, INSTALANDO, ERRO }

    private val contexto: Context = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val escopo = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    var fase by mutableStateOf(Fase.PARADO)
        private set

    /** 0 a 1 enquanto baixa (-1 quando o GitHub não diz o tamanho). */
    var progresso by mutableFloatStateOf(0f)
        private set
    var recado by mutableStateOf("")
        private set

    /** A versão mais nova que o PROCURAR achou no GitHub (null = ainda não procurou ou não achou). */
    var noGithub by mutableStateOf<String?>(null)
        private set

    val versaoApp: String get() = BuildConfig.VERSION_NAME

    val ocupado: Boolean get() = fase == Fase.PROCURANDO || fase == Fase.BAIXANDO || fase == Fase.INSTALANDO

    /** Esta versão (do jogo ou do GitHub) é mais nova que o app. */
    fun maisNova(versao: String?): Boolean = !versao.isNullOrEmpty() && maisVelha(versaoApp, versao)

    /** O Android deixa este app instalar APK? (a chave "instalar apps desconhecidos" do Android 8 em diante) */
    fun podeInstalar(): Boolean = Build.VERSION.SDK_INT < 26 || contexto.packageManager.canRequestPackageInstalls()

    /** A licença de instalar, guardada para a tela redesenhar (o app confere ao voltar dos ajustes). */
    var licenca by mutableStateOf(podeInstalar())
        private set

    fun conferirLicenca() {
        licenca = podeInstalar()
        if (licenca && fase == Fase.ERRO && recado.startsWith("FALTA UMA LICENÇA")) esquecerErro()
    }

    /** Abre a tela do Android para ligar "permitir desta fonte" para o app. */
    fun pedirLicenca() {
        if (Build.VERSION.SDK_INT < 26) return
        try {
            contexto.startActivity(
                Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${contexto.packageName}"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        } catch (e: Exception) {
            recado = "ABRA OS AJUSTES DO ANDROID > APPS > SOUL STRIKE CONTROLE > INSTALAR APPS DESCONHECIDOS"
        }
    }

    /** PROCURAR: qual a última versão publicada no GitHub. */
    fun procurar() {
        if (ocupado) return
        fase = Fase.PROCURANDO
        recado = ""
        escopo.launch {
            val tag = try {
                val con = abrir("$API/releases/latest")
                con.setRequestProperty("Accept", "application/vnd.github+json")
                val texto = con.inputStream.use { String(it.readBytes(), Charsets.UTF_8) }
                JSONObject(texto).optString("tag_name").removePrefix("v")
            } catch (e: Exception) {
                ""
            }
            naTela {
                fase = Fase.PARADO
                if (tag.isEmpty()) {
                    recado = "NÃO DEU PARA FALAR COM O GITHUB. O CELULAR ESTÁ COM INTERNET?"
                } else {
                    noGithub = tag
                    recado = if (maisNova(tag)) "" else "VOCÊ JÁ ESTÁ NA VERSÃO MAIS NOVA (v$versaoApp)"
                }
            }
        }
    }

    /** Baixa o APK da versão ``versao`` (a do jogo) e abre o instalador. */
    fun atualizar(versao: String) {
        if (ocupado) return
        if (!podeInstalar()) {
            fase = Fase.ERRO
            recado = "FALTA UMA LICENÇA: TOQUE EM PERMITIR, LIGUE \"PERMITIR DESTA FONTE\" E VOLTE AQUI"
            return
        }
        fase = Fase.BAIXANDO
        progresso = 0f
        recado = ""
        escopo.launch {
            val pasta = File(contexto.cacheDir, "atualizacao")
            pasta.deleteRecursively()
            pasta.mkdirs()
            val arquivo = File(pasta, "SoulStrikeControle.apk")
            // a Release da versão do jogo; se ela ainda não saiu, a última publicada
            var baixou = false
            for (u in listOf("$REPO/releases/download/v$versao/$APK", "$REPO/releases/latest/download/$APK")) {
                if (baixar(u, arquivo) && novaDeVerdade(arquivo)) {
                    baixou = true
                    break
                }
            }
            if (!baixou) {
                naTela {
                    fase = Fase.ERRO
                    recado = "NÃO ACHEI O APK NOVO NO GITHUB. O CELULAR ESTÁ COM INTERNET? A VERSÃO JÁ FOI PUBLICADA?"
                }
                return@launch
            }
            naTela { fase = Fase.INSTALANDO }
            try {
                instalar(arquivo)
            } catch (e: Exception) {
                naTela {
                    fase = Fase.ERRO
                    recado = "O ANDROID NÃO ABRIU O INSTALADOR (${e.javaClass.simpleName})"
                }
            }
        }
    }

    /** O instalador do Android respondeu (RecebeInstalacao). */
    fun terminou(ok: Boolean, mensagem: String?) {
        naTela {
            if (ok) {
                fase = Fase.PARADO
                recado = ""
            } else {
                fase = Fase.ERRO
                recado = if (mensagem.isNullOrEmpty()) "A INSTALAÇÃO FOI CANCELADA" else "NÃO INSTALOU: ${mensagem.uppercase()}"
            }
        }
    }

    fun esquecerErro() {
        if (fase == Fase.ERRO) fase = Fase.PARADO
        recado = ""
    }

    // ── por dentro ────────────────────────────

    private fun abrir(url: String): HttpURLConnection {
        val con = URL(url).openConnection() as HttpURLConnection
        con.connectTimeout = 15000
        con.readTimeout = 20000
        con.instanceFollowRedirects = true             // o GitHub manda para o servidor dos arquivos
        con.setRequestProperty("User-Agent", "SoulStrikeControle/$versaoApp")
        return con
    }

    private fun baixar(url: String, destino: File): Boolean {
        val parcial = File(destino.path + ".parte")
        return try {
            val con = abrir(url)
            if (con.responseCode !in 200..299) {
                con.disconnect()
                return false
            }
            val total = con.contentLengthLong
            var feito = 0L
            var mostrado = -1
            con.inputStream.use { entrada ->
                parcial.outputStream().use { saida ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = entrada.read(buf)
                        if (n < 0) break
                        saida.write(buf, 0, n)
                        feito += n
                        val pct = if (total > 0) (feito * 100 / total).toInt() else -1
                        if (pct != mostrado) {
                            mostrado = pct
                            naTela { progresso = if (pct >= 0) pct / 100f else -1f }
                        }
                    }
                }
            }
            if (total > 0 && feito != total) return false
            destino.delete()
            parcial.renameTo(destino)
        } catch (e: Exception) {
            parcial.delete()
            false
        }
    }

    /** O APK baixado é deste app e mais novo que o instalado (o "latest" do GitHub pode ser velho). */
    private fun novaDeVerdade(apk: File): Boolean {
        val info = try {
            contexto.packageManager.getPackageArchiveInfo(apk.path, 0)
        } catch (e: Exception) {
            null
        } ?: return false
        return info.packageName == contexto.packageName &&
            PackageInfoCompat.getLongVersionCode(info) > BuildConfig.VERSION_CODE.toLong()
    }

    private fun instalar(apk: File) {
        val instalador = contexto.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(contexto.packageName)
        params.setSize(apk.length())
        if (Build.VERSION.SDK_INT >= 31) {
            // depois da primeira vez, o app vira o "instalador" dele mesmo e o Android pode nem perguntar
            params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED)
        }
        val id = instalador.createSession(params)
        instalador.openSession(id).use { sessao ->
            sessao.openWrite("SoulStrikeControle.apk", 0, apk.length()).use { saida ->
                apk.inputStream().use { it.copyTo(saida) }
                sessao.fsync(saida)
            }
            val aviso = Intent(contexto, RecebeInstalacao::class.java).setAction(RecebeInstalacao.ACAO)
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
            val pendente = PendingIntent.getBroadcast(contexto, id, aviso, flags)
            sessao.commit(pendente.intentSender)
        }
    }

    private fun naTela(bloco: () -> Unit) {
        main.post(bloco)
    }

    companion object {
        const val REPO = "https://github.com/cauapbritto/joguin"
        const val API = "https://api.github.com/repos/cauapbritto/joguin"
        const val APK = "SoulStrikeControle.apk"

        /** a < b ("1.59.0" < "1.60.0"); versões que não são números não contam. */
        fun maisVelha(a: String, b: String): Boolean {
            val pa = a.split(".").map { it.toIntOrNull() ?: 0 }
            val pb = b.split(".").map { it.toIntOrNull() ?: 0 }
            if (pa.all { it == 0 } || pb.all { it == 0 }) return false
            for (i in 0 until maxOf(pa.size, pb.size)) {
                val x = pa.getOrElse(i) { 0 }
                val y = pb.getOrElse(i) { 0 }
                if (x != y) return x < y
            }
            return false
        }
    }
}
