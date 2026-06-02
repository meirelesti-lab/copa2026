# Copa do Mundo 2026 🏆

Site estático gerado automaticamente com todos os jogos, placares e filtros.
Publicado em: **https://meirelesti-lab.github.io/copa2026**

---

## Setup (uma vez só)

```bash
git clone https://github.com/meirelesti-lab/copa2026.git
cd copa2026
pip install -r requirements.txt
```

1. Cadastro gratuito em https://www.football-data.org/client/register
2. Crie o arquivo `.env` na raiz do projeto:
   ```
   FOOTBALL_API_KEY=sua_chave_aqui
   ```
3. Configure o GitHub Pages:
   - Settings → Pages → Deploy from branch → `main` → `/ (root)`

---

## Uso diário

```bash
python atualizar.py
```

### O que acontece

1. Busca resultados em football-data.org (endpoint `/v4/competitions/WC/matches`)
2. Atualiza `resultados.json` com placares dos jogos encerrados
3. Gera `index.html` atualizado com design dark e filtros interativos
4. Faz `git push` automático para GitHub Pages
5. Site atualiza em ~1 minuto em https://meirelesti-lab.github.io/copa2026

---

## Agendamento automático (opcional)

Para rodar automaticamente todo dia às 8h no Mac:

```bash
crontab -e
```

Adicione a linha (ajuste o caminho):

```
0 8 * * * cd /caminho/para/copa2026 && python atualizar.py >> log.txt 2>&1
```

---

## Estrutura

```
copa2026/
├── atualizar.py        ← script principal (rodar diariamente)
├── gerar_html.py       ← gera o index.html
├── dados_jogos.py      ← dados fixos dos 90 jogos + mapeamento de nomes
├── index.html          ← gerado automaticamente (não editar)
├── requirements.txt
├── .gitignore
└── README.md
```

## Notas

- Limite de 10 req/min no plano gratuito — mais que suficiente
- `.env` e `resultados.json` ficam apenas localmente (`.gitignore`)
- Apenas `index.html` vai para o GitHub
