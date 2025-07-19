import discord
import requests
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv
import os
from urllib.parse import urlparse  # Para extrair domínio do link

# Carrega as variáveis do .env (como o TOKEN do bot)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intents e inicialização do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Produtos sendo monitorados
produtos = {}

# Tarefa que verifica os preços periodicamente
async def verificar_precos():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for url, dados in produtos.items():
            preco_atual = extrair_preco(url)
            if preco_atual is not None and preco_atual < dados['preco']:
                canal = bot.get_channel(dados['canal_id'])
                await canal.send(
                    f"📉 O produto em {url} abaixou de preço!\n"
                    f"De: R${dados['preco']:.2f} → Para: R${preco_atual:.2f}"
                )
                produtos[url]['preco'] = preco_atual
        await asyncio.sleep(3600)  # Espera 1 hora entre verificações

# 🧠 Extrai o preço do produto a partir da URL
def extrair_preco(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": url,  # Referer apontando para a página do produto
        "Origin": "https://www.deiapresente.com.br",
    }

    try:
        dominio = urlparse(url).netloc

        if "deiapresente.com.br" in dominio:
            # Extrai o slug do produto a partir da URL
            slug = url.rstrip('/').split('/')[-1]
            api_url = f"https://www.deiapresente.com.br/web_api/products/{slug}"

            resposta = requests.get(api_url, headers=headers)
            if resposta.status_code == 200:
                dados = resposta.json()
                preco = float(dados.get("price", 0))
                return preco
            else:
                print(f"❌ Falha ao acessar a API da loja: {resposta.status_code}")
                return None

        else:
            print(f"❌ Site {dominio} ainda não suportado.")
            return None

    except Exception as e:
        print(f"❌ Erro ao extrair preço: {e}")
        return None


# 📩 Comando oficial: !monitorar <URL> <preço>
@bot.command(name="monitorar")
async def monitorar(ctx, url: str, preco_alvo: float):
    preco_atual = extrair_preco(url)

    if preco_atual is None:
        await ctx.send("Não consegui extrair o preço. Verifica esse link, parça.")
        return

    produtos[url] = {
        'preco': preco_alvo,
        'canal_id': ctx.channel.id
    }

    await ctx.send(f"✅ Produto monitorado! Avisarei se o preço cair abaixo de R${preco_alvo:.2f}")

# 🤖 Quando o bot estiver pronto
@bot.event
async def on_ready():
    print("🤖 Bot de preços está online!")
    bot.loop.create_task(verificar_precos())  # Inicia verificação de preços

# 🚀 Inicia o bot
bot.run(TOKEN)
