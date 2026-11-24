package io.github.cauapbritto.soulstrike.controle.telas

import android.Manifest
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.Tela
import io.github.cauapbritto.soulstrike.controle.rede.Endereco
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.corVaga
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.u
import kotlinx.coroutines.delay
import java.util.concurrent.Executor
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/** ESCANEAR: a câmera lê o QR da TV e o app já entra na vaga dele. */
@Composable
fun TelaCamera() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val m = LocalMedidas.current
    val dono = remember(ctx) { ctx.dono() }
    var permitido by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(ctx, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    var pediu by remember { mutableStateOf(false) }
    val pedir = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        permitido = ok
        pediu = true
    }
    LaunchedEffect(Unit) {
        if (!permitido) pedir.launch(Manifest.permission.CAMERA)
    }
    var lido by remember { mutableStateOf<Endereco?>(null) }
    var recado by remember { mutableStateOf<String?>(null) }
    var camera by remember { mutableStateOf<Camera?>(null) }
    var lanterna by remember { mutableStateOf(false) }
    var semLeitor by remember { mutableStateOf(false) }

    LaunchedEffect(lido) {
        val e = lido ?: return@LaunchedEffect
        app.vibrador.tocar("leu")
        delay(700)
        app.conectar(e)
    }
    LaunchedEffect(recado) {
        if (recado != null) {
            delay(2500)
            recado = null
        }
    }

    Box(
        Modifier
            .fillMaxSize()
            .drawBehind { drawRect(Color.Black) }
    ) {
        if (permitido && dono != null) {
            CameraComQr(
                dono,
                aoLer = { texto ->
                    if (lido == null) {
                        val e = Endereco.ler(texto)
                        if (e == null || !Endereco.redeLocal(e.host)) {
                            if (recado == null) app.vibrador.tocar("erro")
                            recado = "ESSE QR NÃO É DO JOGO: APONTE PARA O QR DA TV"
                        } else {
                            lido = e
                        }
                    }
                },
                aoAbrir = { camera = it },
                aoSemLeitor = { semLeitor = true },
            )
            Mira(lido != null)
        } else {
            Column(
                Modifier
                    .align(Alignment.Center)
                    .widthIn(max = 460.u),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(14.u),
            ) {
                Icone(R.drawable.ic_qr, 64, sombra = true)
                Texto(
                    if (pediu) "SEM A CÂMERA NÃO DÁ PARA LER O QR. PERMITA NOS AJUSTES OU DIGITE O ENDEREÇO."
                    else "O APP PRECISA DA CÂMERA PARA LER O QR DA TV.",
                    cor = Cores.Bone, alinhar = TextAlign.Center,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.u)) {
                    Botao("PERMITIR", tipo = TipoBotao.VERDE) {
                        if (pediu) app.abrirAjustesDoAndroid?.invoke() else pedir.launch(Manifest.permission.CAMERA)
                    }
                    Botao("DIGITAR ENDEREÇO", icone = R.drawable.ic_teclado) { app.tela = Tela.DIGITAR }
                }
            }
        }
        Row(
            Modifier
                .fillMaxWidth()
                .padding(12.u),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Botao("VOLTAR", icone = R.drawable.ic_voltar, altura = 32) { app.tela = Tela.MENU }
            Texto(
                "APONTE PARA O QR DA TV", Modifier.weight(1f), tam = 16, sombra = true,
                alinhar = TextAlign.Center, linhas = 1,
            )
            val cam = camera
            if (cam != null && cam.cameraInfo.hasFlashUnit()) {
                Botao("LANTERNA", icone = R.drawable.ic_lanterna, altura = 32, ligado = lanterna) {
                    lanterna = !lanterna
                    try {
                        cam.cameraControl.enableTorch(lanterna)
                    } catch (e: Exception) {
                        lanterna = false
                    }
                }
            } else {
                Spacer(Modifier.padding(start = 96.u))
            }
        }
        Column(
            Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 14.u),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.u),
        ) {
            val e = lido
            if (e != null) {
                val v = e.vaga
                Row(
                    Modifier
                        .widthIn(min = 360.u)
                        .moldura(m, fundo = Color(0xFF15301E), luz = Color(0xFF2C6A3A), sombra = Color(0xFF0A1A10))
                        .padding(horizontal = 14.u, vertical = 10.u),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.u),
                ) {
                    if (v in 1..4) {
                        Box(
                            Modifier
                                .moldura(m, fundo = corVaga(v), luz = Color.White.copy(alpha = 0.35f), sombra = Color.Black.copy(alpha = 0.35f))
                                .padding(horizontal = 8.u, vertical = 6.u)
                        ) { Texto("P$v", tam = 16, cor = Color.White, linha = 16) }
                    }
                    Column(verticalArrangement = Arrangement.spacedBy(6.u)) {
                        Texto(if (v in 1..4) "ACHEI! JOGADOR $v" else "ACHEI O JOGO!", tam = 16, cor = Cores.Moss, sombra = true)
                        Texto("${e.host} · ENTRANDO...", cor = Cores.Bone)
                    }
                }
            } else {
                val msg = recado ?: app.canal.erro
                    ?: if (semLeitor) "O LEITOR DE QR NÃO ABRIU NESTE CELULAR: DIGITE O ENDEREÇO" else null
                Texto(
                    msg ?: "O QR APARECE NA TV DEPOIS QUE O MODO É ESCOLHIDO",
                    cor = if (msg != null) Color(0xFFFF8A80) else Cores.Bone, alinhar = TextAlign.Center,
                )
                Botao("SEM QR? DIGITAR ENDEREÇO", icone = R.drawable.ic_teclado, altura = 32) { app.tela = Tela.DIGITAR }
            }
        }
    }
}

/** A moldura de mira no meio (dourada; verde quando leu) e a linha vermelha que corre. */
@Composable
private fun Mira(leu: Boolean) {
    val m = LocalMedidas.current
    val t = rememberInfiniteTransition(label = "mira")
    val linha by t.animateFloat(
        initialValue = 0.08f, targetValue = 0.92f,
        animationSpec = infiniteRepeatable(tween(1600, easing = LinearEasing), RepeatMode.Reverse),
        label = "linha",
    )
    Box(
        Modifier
            .fillMaxSize()
            .drawBehind {
                val lado = minOf(size.height * 0.6f, size.width * 0.42f)
                val x = (size.width - lado) / 2f
                val y = (size.height - lado) / 2f - m.px(4)
                val escuro = Color.Black.copy(alpha = 0.5f)
                drawRect(escuro, Offset.Zero, Size(size.width, y))
                drawRect(escuro, Offset(0f, y + lado), Size(size.width, size.height - y - lado))
                drawRect(escuro, Offset(0f, y), Size(x, lado))
                drawRect(escuro, Offset(x + lado, y), Size(size.width - x - lado, lado))
                val cor = if (leu) Cores.Moss else Cores.Brass
                val g = m.px(4)
                val l = m.px(28)
                drawRect(cor, Offset(x - g, y - g), Size(l, g))
                drawRect(cor, Offset(x - g, y - g), Size(g, l))
                drawRect(cor, Offset(x + lado + g - l, y - g), Size(l, g))
                drawRect(cor, Offset(x + lado, y - g), Size(g, l))
                drawRect(cor, Offset(x - g, y + lado), Size(l, g))
                drawRect(cor, Offset(x - g, y + lado + g - l), Size(g, l))
                drawRect(cor, Offset(x + lado + g - l, y + lado), Size(l, g))
                drawRect(cor, Offset(x + lado, y + lado + g - l), Size(g, l))
                if (!leu) {
                    val ly = y + lado * linha
                    drawRect(Color(0x66FF3030), Offset(x - m.px(6), ly - m.px(2)), Size(lado + m.px(12), m.px(5)))
                    drawRect(Color(0xFFFF4040), Offset(x - m.px(6), ly), Size(lado + m.px(12), m.px(1)))
                }
            }
    )
}

/** A imagem da câmera (CameraX) com o leitor de QR (ML Kit, sem internet) em cada quadro. */
@Composable
private fun CameraComQr(dono: LifecycleOwner, aoLer: (String) -> Unit, aoAbrir: (Camera?) -> Unit, aoSemLeitor: () -> Unit) {
    val ctx = LocalContext.current
    val lerAgora = rememberUpdatedState(aoLer)
    val abrirAgora = rememberUpdatedState(aoAbrir)
    val vista = remember {
        PreviewView(ctx).apply {
            implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            scaleType = PreviewView.ScaleType.FILL_CENTER
        }
    }
    AndroidView(factory = { vista }, modifier = Modifier.fillMaxSize())
    DisposableEffect(dono) {
        val principal = ContextCompat.getMainExecutor(ctx)
        val fila: ExecutorService = Executors.newSingleThreadExecutor()
        val leitor = LeitorQr(principal) { texto -> lerAgora.value(texto) }
        if (leitor.leitor == null) aoSemLeitor()
        val futuro = ProcessCameraProvider.getInstance(ctx)
        var provedor: ProcessCameraProvider? = null
        var ativo = true
        futuro.addListener({
            if (!ativo) return@addListener
            val p = try {
                futuro.get()
            } catch (e: Exception) {
                null
            } ?: return@addListener
            provedor = p
            val previa = Preview.Builder().build()
            previa.setSurfaceProvider(vista.surfaceProvider)
            val analise = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            analise.setAnalyzer(fila, leitor)
            try {
                p.unbindAll()
                abrirAgora.value(p.bindToLifecycle(dono, CameraSelector.DEFAULT_BACK_CAMERA, previa, analise))
            } catch (e: Exception) {
                abrirAgora.value(null)
            }
        }, principal)
        onDispose {
            ativo = false
            try {
                provedor?.unbindAll()
            } catch (e: Exception) {
            }
            leitor.fechar()
            fila.shutdown()
            abrirAgora.value(null)
        }
    }
}

/** Procura QR em cada quadro da câmera e avisa o texto lido (na thread principal). */
private class LeitorQr(private val principal: Executor, private val aoLer: (String) -> Unit) : ImageAnalysis.Analyzer {
    /** null = o leitor não abriu neste celular (a tela avisa para digitar o endereço). */
    val leitor: BarcodeScanner? = try {
        BarcodeScanning.getClient(BarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build())
    } catch (e: Throwable) {
        null
    }

    @Volatile
    private var fechado = false

    @androidx.annotation.OptIn(markerClass = [ExperimentalGetImage::class])
    override fun analyze(proxy: ImageProxy) {
        val l = leitor
        val quadro = proxy.image
        if (l == null || quadro == null || fechado) {
            proxy.close()
            return
        }
        // um quadro estranho (ou o leitor fechando no meio) nunca derruba o app: pula o quadro
        try {
            val img = InputImage.fromMediaImage(quadro, proxy.imageInfo.rotationDegrees)
            l.process(img)
                .addOnSuccessListener { codigos ->
                    val texto = codigos?.firstNotNullOfOrNull { it?.rawValue }
                    if (texto != null && !fechado) principal.execute { aoLer(texto) }
                }
                .addOnCompleteListener { proxy.close() }
        } catch (e: Throwable) {
            proxy.close()
        }
    }

    fun fechar() {
        fechado = true
        try {
            leitor?.close()
        } catch (e: Exception) {
        }
    }
}

/** A Activity (dona do ciclo de vida que a câmera segue). */
private fun Context.dono(): LifecycleOwner? {
    var c: Context? = this
    while (c != null) {
        if (c is LifecycleOwner) return c
        c = (c as? ContextWrapper)?.baseContext
    }
    return null
}
