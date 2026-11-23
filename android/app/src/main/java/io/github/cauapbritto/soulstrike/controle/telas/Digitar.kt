package io.github.cauapbritto.soulstrike.controle.telas

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import io.github.cauapbritto.soulstrike.controle.LocalApp
import io.github.cauapbritto.soulstrike.controle.R
import io.github.cauapbritto.soulstrike.controle.Tela
import io.github.cauapbritto.soulstrike.controle.rede.Descoberta
import io.github.cauapbritto.soulstrike.controle.rede.Endereco
import io.github.cauapbritto.soulstrike.controle.ui.Botao
import io.github.cauapbritto.soulstrike.controle.ui.Cabecalho
import io.github.cauapbritto.soulstrike.controle.ui.Cores
import io.github.cauapbritto.soulstrike.controle.ui.Icone
import io.github.cauapbritto.soulstrike.controle.ui.LocalMedidas
import io.github.cauapbritto.soulstrike.controle.ui.Texto
import io.github.cauapbritto.soulstrike.controle.ui.TipoBotao
import io.github.cauapbritto.soulstrike.controle.ui.aoTocar
import io.github.cauapbritto.soulstrike.controle.ui.moldura
import io.github.cauapbritto.soulstrike.controle.ui.piscando
import io.github.cauapbritto.soulstrike.controle.ui.u

/** DIGITAR ENDEREÇO: teclado de números grande, o endereço da TV e os últimos jogos. */
@Composable
fun TelaDigitar() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val m = LocalMedidas.current
    val recentes = remember { app.prefs.recentes() }
    var texto by remember {
        mutableStateOf(recentes.firstOrNull()?.host ?: Descoberta.prefixoDaRede(ctx) ?: "")
    }
    var erro by remember { mutableStateOf<String?>(null) }
    val pisca by piscando(450L)

    fun tecla(c: String) {
        erro = null
        app.canal.erro = null
        if (texto.length < 21) texto += c
    }

    fun conectar() {
        val end = Endereco.ler(texto)
        erro = when {
            end == null -> "FALTA ALGUMA COISA: SÃO 4 NÚMEROS COM PONTO (EX.: 192.168.0.10)"
            !Endereco.redeLocal(end.host) -> "ESSE NÃO É UM ENDEREÇO DE CASA (COMEÇA COM 192.168, 10 OU 172)"
            else -> null
        }
        if (end != null && erro == null) app.conectar(end)
    }

    Column(Modifier.fillMaxSize()) {
        Cabecalho {
            Botao("VOLTAR", icone = R.drawable.ic_voltar, altura = 32) { app.tela = Tela.MENU }
            Texto("DIGITAR ENDEREÇO", tam = 16, sombra = true, linhas = 1)
        }
        Row(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 16.u, vertical = 14.u),
            horizontalArrangement = Arrangement.spacedBy(20.u),
        ) {
            Column(Modifier.weight(1f).fillMaxHeight(), verticalArrangement = Arrangement.spacedBy(8.u)) {
                Texto("O ENDEREÇO APARECE NA TV, EMBAIXO DOS QR:", cor = Cores.Muted)
                Texto("OU ABRA http://192.168.0.10:5000/?player=N", cor = Cores.Bone, linhas = 1)
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 6.u)
                        .moldura(m, fundo = Cores.Bolso, luz = Color.Black, sombra = Cores.Line)
                        .padding(horizontal = 14.u, vertical = 14.u),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Texto(texto, tam = 24, linhas = 1, sombra = true)
                    Spacer(
                        Modifier
                            .padding(start = 2.u)
                            .size(12.u, 24.u)
                            .drawBehind { if (pisca) drawRect(Cores.Brass) }
                    )
                }
                val msg = erro ?: app.canal.erro
                if (msg != null) Texto(msg, cor = Color(0xFFFF8A80))
                else Texto("PORTA ${Endereco.PORTA}, A DO JOGO", cor = Cores.Muted)
                if (recentes.isNotEmpty()) {
                    Spacer(Modifier.height(4.u))
                    Texto("RECENTES", cor = Cores.Brass)
                    for (j in recentes.take(3)) {
                        val apertado = remember { mutableStateOf(false) }
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .graphicsLayer { translationY = if (apertado.value) m.px(2) else 0f }
                                .moldura(m, fundo = Cores.Ink2)
                                .aoTocar(apertado = apertado) { app.conectar(Endereco(j.host, j.porta, 0)) }
                                .padding(horizontal = 10.u, vertical = 8.u),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.u),
                        ) {
                            Icone(R.drawable.ic_pc, 16)
                            Texto(if (j.porta == Endereco.PORTA) j.host else "${j.host}:${j.porta}", linhas = 1)
                            Spacer(Modifier.weight(1f))
                            Texto(listOf(j.nome, quando(j.quando)).filter { it.isNotEmpty() }.joinToString(" · "), cor = Cores.Muted, linhas = 1)
                        }
                    }
                }
            }
            Column(Modifier.weight(1f).fillMaxHeight(), verticalArrangement = Arrangement.spacedBy(10.u)) {
                val linhas = listOf(listOf("1", "2", "3"), listOf("4", "5", "6"), listOf("7", "8", "9"), listOf(".", "0", "<"))
                for (linha in linhas) {
                    Row(Modifier.weight(1f).fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.u)) {
                        for (c in linha) {
                            if (c == "<") {
                                Botao(
                                    "APAGAR", Modifier.weight(1f).fillMaxHeight(), tipo = TipoBotao.VERMELHO,
                                    icone = R.drawable.ic_voltar, naHora = true,
                                ) {
                                    erro = null
                                    if (texto.isNotEmpty()) texto = texto.dropLast(1)
                                }
                            } else {
                                Botao(c, Modifier.weight(1f).fillMaxHeight(), tam = 16, naHora = true) { tecla(c) }
                            }
                        }
                    }
                }
                Botao(
                    "CONECTAR", Modifier.fillMaxWidth().height(56.u), tipo = TipoBotao.VERDE, tam = 16,
                    sub = "E ESCOLHER A VAGA", ativo = texto.isNotEmpty(),
                ) { conectar() }
            }
        }
    }
}
