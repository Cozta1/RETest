# Análise defensiva — site falso "Drogaria São Paulo"

**Alvo:** `https://drogariasaopaulomatrizsp.com/` (loja) e `https://pagamento.drogariasaopaulomatrizsp.com/` (pagamento)
**Marca imitada:** Drogaria São Paulo / Grupo DPSP (site oficial legítimo: `drogariasaopaulo.com.br`)
**Data da análise:** 2026-10-08
**Método:** coleta passiva (OSINT) + requisições HTTP públicas. **Não** houve varredura de portas na infraestrutura, exploração de falhas, invasão nem envio de dados reais de pagamento.

---

## 1. Resumo

Loja WooCommerce clonada da marca Drogaria São Paulo, com o módulo de pagamento **desacoplado**: a vitrine é WordPress hospedado na **Hostinger** atrás da **Cloudflare** (que oculta o IP de origem), enquanto a captura do pagamento roda num app **Next.js separado na Vercel**. O domínio foi **registrado em 07/10/2026** (um dia antes da análise), padrão típico de golpe descartável.

## 2. Domínio e registro (RDAP)

| Campo | Valor |
|---|---|
| Registro (criação) | **2026-10-07 12:22:31 UTC** |
| Última alteração | 2026-10-07 12:34:35 UTC |
| Expiração | 2027-10-07 12:22:31 UTC (registro de 1 ano, o mínimo) |
| Registrador | **Hosting Concepts B.V. d/b/a Registrar.eu** (Openprovider) |
| Status | `clientTransferProhibited` |
| Nameservers | `ALINA.NS.CLOUDFLARE.COM`, `KEATON.NS.CLOUDFLARE.COM` |
| crt.sh (Certificate Transparency) | sem certificados listados até a análise (domínio novo demais) |

## 3. Loja — `drogariasaopaulomatrizsp.com`

- **Plataforma:** WordPress 7.0.2 + WooCommerce, tema **Woodmart**.
- **Infra:** servidor via **Cloudflare** (IPs `172.67.193.60`, `104.21.20.171` — são da Cloudflare, não do servidor real). Sinais fortes de **Hostinger** como hospedagem de origem (namespaces REST `hostinger-reach`, `hostinger-tools-plugin`, `hostinger-ai-assistant`, `hostinger-amplitude`, `hostinger-easy-onboarding`).
- **Plugins relevantes:** `woo-custom-installments` (parcelas/PIX com selo de desconto), `shipping-simulator-for-woocommerce`, `elementor`, `revslider`, `contact-form-7`, `widget-countdown` (falsa urgência), `safe-svg`, `adtribes` (gera feeds de produto p/ Google/Meta Shopping — usado para **anunciar** o golpe), `jetpack`, `mc4wp`.
- **`duplicator/v1` na API REST:** indica que o site foi **importado de um pacote pronto** (plugin Duplicator), coerente com clone/kit reutilizável.
- **Superfície exposta:** `xmlrpc.php` (403), `wp-json/wc/store/v1/*` aberta (lista produtos sem auth), `/loja/`, `/carrinho/`, `/finalizar-compra/` (redireciona p/ carrinho quando vazio).
- **Preços:** valores de varejo normais na Store API (ex.: Pantene R$16,95; La Roche-Posay Lipikar R$122,81; Isdin R$112,02) — o "metade do preço" aparece no front via selos/comparação, isca clássica.

## 4. Pagamento — `pagamento.drogariasaopaulomatrizsp.com` (SEPARADO)

- **Hospedagem distinta da loja:** **Vercel**. `CNAME → ba8525e53af3315a.vercel-dns-016.com`, IPs `216.150.1.129`/`216.150.16.129`, header `server: Vercel`.
- **Framework:** **Next.js** (caminho `/_next/static` presente; `favicon.ico` responde 200).
- **Rotas:** raiz `/` e ~30 caminhos comuns (`/pay`, `/pix`, `/checkout`, `/pagar`, `/qrcode`, `/api/pix`, `/status`, `/callback`, `/webhook`, `/retorno`, etc.) retornam **404**.
- **Rota real CONFIRMADA:** `/pay/[checkoutid]` — vista no trace de rede do app (`/_next/static/chunks/app/pay/%5Bcheckoutid%5D/layout-*.js`). Ou seja, é rota dinâmica por pedido (um `checkoutid` gerado no momento da compra). O HTML público da loja **não referencia** o subdomínio — o link é gerado no servidor ao fechar o pedido, por isso não é enumerável publicamente sem criar um pedido real.

## 5. Arquitetura do golpe ("o processo por trás")

1. Registram domínio parecido com a marca (typosquatting + "matrizsp").
2. Sobem um WordPress/WooCommerce clonado (kit Duplicator) na Hostinger e colocam a **Cloudflare na frente** para esconder o IP real e dar HTTPS instantâneo.
3. Preenchem o catálogo com produtos reais a preços atrativos + contador regressivo (urgência).
4. Geram feeds (AdTribes) para **anunciar** em Google/Meta e atrair tráfego.
5. No checkout, desviam o pagamento para um **app Next.js na Vercel** separado. Desacoplar significa: se a loja cair, o coletor de pagamento sobrevive (e vice-versa), e dificulta ligar o dinheiro ao site.
6. O recebedor real (chave PIX / CNPJ) só aparece ao gerar uma cobrança — **não foi gerada** nesta análise para não inserir dados pessoais.

## 5b. Captura do pagamento — PIX decodificado (prova-chave)

Pedido de teste feito **manualmente no navegador pelo operador** (sem pagar). O "PIX copia e cola" gerado foi decodificado offline (`pix_decode.py`). CRC16 **válido** (`4EDC`), payload autêntico.

| Campo PIX (EMV) | Valor |
|---|---|
| Tipo | **Dinâmico / uso único** (campo 01 = 12) |
| Valor | **R$ 77,75** |
| **Recebedor (nome)** | **`NEW LEVEL LTDA`** |
| Cidade do recebedor | **SÃO PAULO** |
| **PSP / gateway** | **Pagsmile** — `qrcode.pagsmile.com.br/qrs1/v2/010IjMxwqYaLO1YzG5xVrC1NWxAZZHTxzUaDgnD76c8EY6` |
| Chave PIX | ausente (dinâmico via PSP — fundos roteiam pela Pagsmile até o estabelecimento) |
| txid | `***` (mascarado) |

**Significado:** o dinheiro **não** vai direto para uma chave PIX pessoal; passa pela **Pagsmile** (processador de pagamentos legítimo) até a conta do estabelecimento **NEW LEVEL LTDA**. A Pagsmile é obrigada a ter **KYC** (CNPJ, responsável, conta de liquidação) desse recebedor — por isso a denúncia ao compliance da Pagsmile é o caminho mais rápido para **congelar o recebimento e identificar o CNPJ** por trás do golpe.

> Observação: "NEW LEVEL LTDA" é o nome do estabelecimento cadastrado no PSP. Pode ser a empresa do golpista, uma empresa-laranja ou um sub-merchant. Isso só a Pagsmile/Bacen confirmam. Evidência visual em `evidencia-pix-qrcode.png`.

## 6. Indicadores (IOCs)

```
Domínio loja     : drogariasaopaulomatrizsp.com
Domínio pagamento: pagamento.drogariasaopaulomatrizsp.com
IPs (Cloudflare) : 172.67.193.60, 104.21.20.171
NS               : ALINA.NS.CLOUDFLARE.COM, KEATON.NS.CLOUDFLARE.COM
IPs (Vercel)     : 216.150.1.129, 216.150.16.129
CNAME pagamento  : ba8525e53af3315a.vercel-dns-016.com
Registrador      : Hosting Concepts B.V. d/b/a Registrar.eu
Criado em        : 2026-10-07
Stack loja       : WordPress 7.0.2 + WooCommerce + Woodmart (Hostinger)
Stack pagamento  : Next.js (Vercel), rota /pay/[checkoutid]
PSP / gateway    : Pagsmile (qrcode.pagsmile.com.br)
Recebedor PIX    : NEW LEVEL LTDA - SAO PAULO
URL PIX dinamico : qrcode.pagsmile.com.br/qrs1/v2/010IjMxwqYaLO1YzG5xVrC1NWxAZZHTxzUaDgnD76c8EY6
```

## 7. Canais de denúncia recomendados

- **Pagsmile — compliance/abuse (PRIORIDADE):** o PSP tem KYC do recebedor `NEW LEVEL LTDA`. Denúncia de fraude/estelionato pode **bloquear o repasse** e expor o CNPJ. Contato via `compliance@pagsmile.com` / canal de denúncia no site da Pagsmile; informe a URL `qrcode.pagsmile.com.br/qrs1/v2/010IjMxwqYaLO1YzG5xVrC1NWxAZZHTxzUaDgnD76c8EY6`, o valor (R$77,75) e o site de origem.
- **Cloudflare abuse** (esconde o IP de origem): https://abuse.cloudflare.com/ → categoria Phishing. Peça o IP de origem e o provedor.
- **Vercel abuse** (hospeda o coletor de pagamento): security/abuse da Vercel, informando o subdomínio `pagamento.*`.
- **Hostinger abuse:** abuse@hostinger.com (hospedagem de origem provável).
- **Registrar.eu / Openprovider abuse:** denúncia de domínio usado em phishing.
- **Google Safe Browsing:** https://safebrowsing.google.com/safebrowsing/report_phish/
- **Drogaria São Paulo / Grupo DPSP:** jurídico da marca tem legitimidade para pedir takedown.
- **SaferNet Brasil:** https://new.safernet.org.br/denuncie ; e registro de **B.O. em delegacia de crimes cibernéticos**.
- **Para capturar o recebedor do PIX** (sem pagar): chegar ao ponto em que a cobrança é gerada e registrar o nome/instituição do titular — material forte para a denúncia bancária e policial.

## 7b. Tentativa de identificar o repositório GitHub do app Vercel

- O deploy Vercel do `pagamento.*` **não expõe código**: raiz `/` retorna 404 com corpo vazio, sem bundles JS públicos, sem source maps; headers (`x-vercel-id: iad1::...`, `server: Vercel`) não revelam o repositório de origem.
- Busca web/GitHub pelo domínio e pelo hash de deploy `ba8525e53af3315a`: **sem resultados**.
- Conclusão: repositório provavelmente **privado** (ou deploy sem Git). Não identificado.
- Lead descartado: `Caiosenas2101/DROGASIL` é protótipo acadêmico de LGPD (sem pagamento, marca Drogasil), **não relacionado**.
- Caminho viável p/ avançar: obter um **link de pagamento real** (pedido de teste, sem pagar) e analisar os assets daquela rota específica + identificar o gateway/recebedor PIX.

## 8. Próximos passos possíveis (com sua autorização)

- Salvar cópias forenses (HTML/HAR) da loja e, se você tiver um link de pedido, do app de pagamento.
- Gerar uma cobrança de teste (sem pagar) para identificar o gateway e o recebedor do PIX.
- Correlacionar IDs de pixel/analytics e feeds para achar **domínios-irmãos** da mesma quadrilha.
