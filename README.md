# NBB Scraper 🏀

Este projeto é um web scraper construído com Scrapy para coletar dados de jogos, times, jogadores e estatísticas de arremessos da liga de basquete brasileira, a NBB (Novo Basquete Brasil). Os dados raspados são persistidos em um banco de dados PostgreSQL.

---

## 🛠️ Ferramentas Utilizadas

O projeto utiliza um conjunto de ferramentas robusto para web scraping, processamento de dados e persistência:

* **Scrapy**: Framework principal para a construção do web scraper.
* **Python**: Linguagem de programação utilizada.
* **PostgreSQL**: Banco de dados para armazenamento dos dados extraídos.
* **Docker**: Para garantir um ambiente de execução consistente e replicável.
* **Git & GitHub**: Controle de versão e hospedagem do código.
* **AWS (Amazon Web Services)**: Infraestrutura de nuvem para hospedar o banco de dados e gerenciar o scraping em produção.

---

## ☁️ Arquitetura de Produção na AWS

A aplicação foi implantada na AWS:

* **EC2 Instance**: Instância em sub-rede pública funcionando como bastion host. Aceita SSH apenas de um IP específico para maior segurança.
* **PostgreSQL RDS**: Banco de dados hospedado em sub-rede privada, inacessível diretamente da internet.
* **CloudWatch**: Logs de execução do container Scrapy enviados em tempo real via driver `awslogs` do Docker.

---

## 🚀 Como Replicar o Projeto Localmente

Você pode executar este projeto em sua máquina local usando Docker e PostgreSQL.

### Pré-requisitos

* Docker instalado.
* Banco de dados PostgreSQL rodando localmente.

### Passo 1: Clone o Repositório

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

### Passo 2: Construa a Imagem Docker

```bash
docker build -t nomedaimagem:tag .
```

### Passo 3: Execute o Container

```bash
docker run \
-e TEMPORADA='2023/2024' \
-e DB_HOST=host.docker.internal \
-e DB_USER=seu_usuario \
-e DB_NAME=seu_banco \
-e DB_PASS=sua_senha \
--name nomedocontainer \
nomedaimagem:tag
```

* `-e TEMPORADA='2023/2024'`: Define a temporada para o scraper. Opções válidas: 2017/2018, 2018/2019, 2019/2020, 2020/2021, 2021/2022, 2022/2023, 2023/2024, 2024/2025.
* `-e DB_HOST=host.docker.internal`: Permite que o container se conecte ao banco de dados local.
* `-e DB_USER`, `-e DB_NAME`, `-e DB_PASS`: Credenciais de acesso ao PostgreSQL local.

Os logs da execução serão exibidos no terminal e os dados inseridos diretamente no banco de dados.

---

Sinta-se à vontade para contribuir com melhorias ou reportar problemas.
