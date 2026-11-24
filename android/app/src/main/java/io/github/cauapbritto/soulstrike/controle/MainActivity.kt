package io.github.cauapbritto.soulstrike.controle

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import io.github.cauapbritto.soulstrike.controle.rede.Descoberta
import io.github.cauapbritto.soulstrike.controle.rede.Endereco

/**
 * A única tela do app: deitada, sem barras do Android, tela sempre acesa e a Wi-Fi no modo de
 * menos atraso enquanto o app está aberto.
 */
class MainActivity : ComponentActivity() {
    private lateinit var app: AppEstado
    private var travaWifi: WifiManager.WifiLock? = null

    private val pedidoRedeLocal = registerForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        app.redeLocalNegada = !ok
        if (ok) app.descoberta.procurar()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        Travamento.instalar(this)                  // antes de tudo: se o app fechar sozinho, o erro fica guardado
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        app = AppEstado.de(this)
        app.pedirRedeLocal = { pedirRedeLocal() }
        app.abrirAjustesDoAndroid = { abrirAjustes() }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (Build.VERSION.SDK_INT >= 28) {
            val a = window.attributes
            a.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            window.attributes = a
        }
        esconderBarras()
        setContent { Raiz(app) }
        if (!temRedeLocal()) pedirRedeLocal()
        lerIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        lerIntent(intent)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) esconderBarras()
        else app.canal.entrada.soltarTudo()      // a cortina do Android desceu: nada fica segurado
    }

    override fun onResume() {
        super.onResume()
        Descoberta.prenderNaWifi(this)
        app.canal.retomar()
        travarWifi(true)
        app.naFrente = true
        app.atualizador.conferirLicenca()          // voltou dos ajustes do Android com a licença ligada?
        if (Build.VERSION.SDK_INT >= 37) app.redeLocalNegada = !temRedeLocal()
    }

    override fun onPause() {
        app.naFrente = false
        app.canal.pausar()
        travarWifi(false)
        super.onPause()
    }

    override fun onDestroy() {
        if (isFinishing) app.canal.sair()          // fechou o app: libera a vaga na hora
        super.onDestroy()
    }

    /** Para testar sem câmera: adb shell am start -n ... --es host 192.168.0.10 --ei vaga 1 */
    private fun lerIntent(intent: Intent?) {
        val host = intent?.getStringExtra("host") ?: return
        val porta = intent.getIntExtra("porta", Endereco.PORTA)
        val vaga = intent.getIntExtra("vaga", 0)
        if (!Endereco.hostValido(host)) return
        intent.removeExtra("host")
        app.conectar(Endereco(host, porta, vaga.coerceIn(0, 4)))
    }

    private fun esconderBarras() {
        val c = WindowCompat.getInsetsController(window, window.decorView)
        c.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        c.hide(WindowInsetsCompat.Type.systemBars())
    }

    private fun temRedeLocal(): Boolean =
        Build.VERSION.SDK_INT < 37 || checkSelfPermission(PERMISSAO_REDE_LOCAL) == PackageManager.PERMISSION_GRANTED

    private fun pedirRedeLocal() {
        if (temRedeLocal()) {
            app.redeLocalNegada = false
            return
        }
        try {
            pedidoRedeLocal.launch(PERMISSAO_REDE_LOCAL)
        } catch (e: Exception) {
            app.redeLocalNegada = true
        }
    }

    private fun abrirAjustes() {
        try {
            startActivity(
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
        } catch (e: Exception) {
            // sem a tela de ajustes: nada a fazer
        }
    }

    @Suppress("DEPRECATION")
    private fun travarWifi(ligar: Boolean) {
        try {
            if (ligar) {
                val trava = travaWifi ?: run {
                    val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager ?: return
                    val modo = if (Build.VERSION.SDK_INT >= 29) WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                    else WifiManager.WIFI_MODE_FULL_HIGH_PERF
                    wm.createWifiLock(modo, "soulstrike:controle").apply { setReferenceCounted(false) }
                        .also { travaWifi = it }
                }
                if (!trava.isHeld) trava.acquire()
            } else {
                travaWifi?.let { if (it.isHeld) it.release() }
            }
        } catch (e: Exception) {
            // sem a trava a Wi-Fi funciona igual, só pode economizar bateria no meio do jogo
        }
    }

    private companion object {
        // Android 17: falar com aparelhos da rede local pede esta permissão em tempo de uso
        const val PERMISSAO_REDE_LOCAL = "android.permission.ACCESS_LOCAL_NETWORK"
    }
}
