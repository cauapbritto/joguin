package io.github.cauapbritto.soulstrike.controle

import android.content.Context
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.displayCutout
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import io.github.cauapbritto.soulstrike.controle.rede.Canal
import io.github.cauapbritto.soulstrike.controle.rede.Descoberta
import io.github.cauapbritto.soulstrike.controle.rede.Endereco
import io.github.cauapbritto.soulstrike.controle.rede.Estado
import io.github.cauapbritto.soulstrike.controle.telas.Aviso
import io.github.cauapbritto.soulstrike.controle.telas.ConfirmarSaida
import io.github.cauapbritto.soulstrike.controle.telas.TelaAjustesApp
import io.github.cauapbritto.soulstrike.controle.telas.TelaCaiu
import io.github.cauapbritto.soulstrike.controle.telas.TelaCamera
import io.github.cauapbritto.soulstrike.controle.telas.TelaConectando
import io.github.cauapbritto.soulstrike.controle.telas.TelaDigitar
import io.github.cauapbritto.soulstrike.controle.telas.TelaJogo
import io.github.cauapbritto.soulstrike.controle.telas.TelaMenu
import io.github.cauapbritto.soulstrike.controle.telas.TelaRede
import io.github.cauapbritto.soulstrike.controle.telas.TelaVagas
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Medidas
import io.github.cauapbritto.soulstrike.controle.ui.fundoDoJogo
import io.github.cauapbritto.soulstrike.controle.ui.linhasDeTv
import io.github.cauapbritto.soulstrike.controle.vibra.Vibrador

/** As telas de antes de conectar (o menu de conexão e os caminhos dele). */
enum class Tela { MENU, CAMERA, REDE, DIGITAR, AJUSTES }

/** Tudo o que o app guarda enquanto está aberto (sobrevive a girar a tela e a voltar do fundo). */
class AppEstado private constructor(context: Context) {
    val contexto: Context = context.applicationContext
    val prefs = Prefs(contexto)
    val vibrador = Vibrador(contexto) { prefs.vibracao }
    val canal = Canal(prefs, vibrador)
    val descoberta = Descoberta(contexto)

    var tela by mutableStateOf(Tela.MENU)
    var clique by mutableStateOf(prefs.cliqueAoTocar)
        private set
    var vibracao by mutableIntStateOf(prefs.vibracao)
        private set

    /** Android 17+: a permissão de rede local foi negada (o app não fala com o jogo). */
    var redeLocalNegada by mutableStateOf(false)
    var pedirRedeLocal: (() -> Unit)? = null
    var abrirAjustesDoAndroid: (() -> Unit)? = null

    /** Tiquinho de vibração dos botões (CLIQUE AO TOCAR). */
    fun toque() {
        if (clique) vibrador.tocar("toque")
    }

    fun mudarVibracao(n: Int) {
        prefs.vibracao = n
        vibracao = n.coerceIn(0, 3)
    }

    fun mudarClique(ligado: Boolean) {
        prefs.cliqueAoTocar = ligado
        clique = ligado
    }

    fun conectar(end: Endereco) {
        Descoberta.prenderNaWifi(contexto)
        descoberta.parar()
        canal.conectar(end)
    }

    companion object {
        @Volatile
        private var unico: AppEstado? = null

        fun de(context: Context): AppEstado =
            unico ?: synchronized(this) { unico ?: AppEstado(context).also { unico = it } }
    }
}

val LocalApp = staticCompositionLocalOf<AppEstado> { error("AppEstado ausente") }

/** A raiz: escolhe a tela pelo estado da conexão e põe o fundo e as linhas de TV. */
@Composable
fun Raiz(app: AppEstado) {
    val densidade = LocalDensity.current
    val medidas = remember(densidade.density, densidade.fontScale) {
        Medidas.para(densidade.density, densidade.fontScale)
    }
    CompositionLocalProvider(LocalApp provides app, LocalMedidas provides medidas) {
        Box(
            Modifier
                .fillMaxSize()
                .fundoDoJogo()
                .linhasDeTv(medidas)
        ) {
            Box(
                Modifier
                    .fillMaxSize()
                    .windowInsetsPadding(WindowInsets.displayCutout)
            ) {
                Telas(app)
            }
        }
    }
}

@Composable
private fun Telas(app: AppEstado) {
    val canal = app.canal
    var sair by remember { mutableStateOf(false) }
    val estado = canal.estado
    when (estado) {
        Estado.FORA -> {
            BackHandler(enabled = app.tela != Tela.MENU) { app.tela = Tela.MENU }
            when (app.tela) {
                Tela.MENU -> TelaMenu()
                Tela.CAMERA -> TelaCamera()
                Tela.REDE -> TelaRede()
                Tela.DIGITAR -> TelaDigitar()
                Tela.AJUSTES -> TelaAjustesApp()
            }
        }
        Estado.CONECTANDO -> {
            BackHandler { canal.sair() }
            TelaConectando()
        }
        Estado.VAGA, Estado.OK, Estado.CAIU -> {
            BackHandler { sair = true }
            if (estado == Estado.VAGA || canal.vaga == 0) TelaVagas() else TelaJogo()
            if (estado == Estado.CAIU) TelaCaiu()
        }
    }
    LaunchedEffect(estado) {
        if (estado == Estado.FORA || estado == Estado.CONECTANDO) sair = false
    }
    if (sair) ConfirmarSaida(aoFechar = { sair = false })
    Aviso()
}
