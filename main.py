import discord
import requests
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intents e inicialização do bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Produtos monitorados
produtos = {}

# 🔁 Verificação periódica de preços
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
        await asyncio.sleep(3600)  # Verifica a cada hora

# 🧠 Função que extrai o preço de uma página da Amazon
def extrair_preco(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resposta = requests.get(url, headers=headers)
        soup = BeautifulSoup(resposta.text, 'html.parser')

        # Tenta múltiplos seletores possíveis de preço na Amazon
        seletores = [
            '#priceblock_ourprice',       # preço normal
            '#priceblock_dealprice',      # preço em oferta
            '#priceblock_saleprice',      # preço de venda
            'span.a-price > span.a-offscreen'  # preço em vários contextos
        ]

        for seletor in seletores:
            preco_elemento = soup.select_one(seletor)
            if preco_elemento:
                preco_texto = preco_elemento.text.strip().replace('R$', '').replace('.', '').replace(',', '.')
                return float(preco_texto)

        print("⚠️ Nenhum seletor de preço funcionou.")

    except Exception as e:
        print(f"❌ Erro ao extrair preço: {e}")
    return None

# 📩 Quando receber mensagem
@bot.event
async def on_message(message):
    await bot.process_commands(message)  # Permite comandos funcionarem com @bot.command()

    if message.author == bot.user:
        return

    if message.content.startswith('!monitorar'):
        parts = message.content.split()

        if len(parts) != 3:
            await message.channel.send("Uso correto: `!monitorar <URL do produto> <preço desejado>`")
            return

        url = parts[1]
        try:
            preco_alvo = float(parts[2])
        except ValueError:
            await message.channel.send("Preço inválido, escreve direito isso aí.")
            return

        preco_atual = extrair_preco(url)
        if preco_atual is None:
            await message.channel.send("Não consegui extrair o preço. Verifica esse link, parça.")
            return

        produtos[url] = {
            'preco': preco_alvo,
            'canal_id': message.channel.id
        }

        await message.channel.send(f"✅ Produto monitorado! Avisarei se o preço cair abaixo de R${preco_alvo:.2f}")

# Evento quando o bot inicia
@bot.event
async def on_ready():
    print("🤖 Noa está online!")
    bot.loop.create_task(verificar_precos()) 

# Inicia o bot
bot.run(TOKEN)
