# Parte 2 — CRUD NoSQL com MongoDB

Projeto da Parte 2 do Trabalho Prático de Engenharia de Dados. O objetivo é
mapear para MongoDB todas as tabelas do modelo relacional da universidade,
representar suas restrições e disponibilizar um CRUD real das estruturas
`usuario`, `estudante`, `vinculo` e `curso`.

A aplicação Flask foi validada com MongoDB Atlas hospedado na AWS. As 16
coleções, validators, índices, carga ETL, operações CRUD e transações foram
confirmadas no banco real.

## Tecnologias

- Python 3;
- Flask;
- MongoDB Atlas hospedado na AWS;
- PyMongo para acesso ao MongoDB real;
- mongomock para testes e execução local em memória;
- unittest;
- HTML e CSS.

## Arquitetura

```text
Interface Flask → serviços → repositórios → MongoDB
```

- `app.py`: aplicação Flask, rotas, formulários e seleção entre mock e Atlas;
- `config.py`: leitura segura das variáveis de ambiente;
- `db.py`: criação dos clientes mongomock e PyMongo;
- `repositories.py`: operações de persistência e fronteira transacional;
- `services.py`: validações, CRUD e regras de integridade;
- `schemas_mongodb.py`: catálogo das 16 coleções, validators e índices;
- `setup_banco.py`: criação ou atualização de coleções, validators e índices;
- `ETL.py`: leitura, validação e carga do dump SQL;
- `templates/` e `static/`: interface web;
- `tests/`: testes automatizados;
- `RELATORIO_PARTE2.md`: relatório técnico final.

## Modelagem MongoDB

Cada tabela relacional foi representada por uma coleção própria:

| Tabela relacional | Coleção MongoDB | Chave principal |
|---|---|---|
| usuario | usuario | `cpf` |
| professor | professor | `mat_professor` |
| departamento | departamento | `cod_depto` |
| curso | curso | `idCurso` |
| estudante | estudante | `mat_estudante` |
| vinculo | vinculo | `idVinculo` |
| projeto | projeto | `id_projeto` |
| plano | plano | (`mat_estudante`, `ano`) |
| disciplina | disciplina | `cod_disc` |
| semestre | semestre | (`ano`, `semestre`) |
| sala | sala | `id_sala` |
| horario | horario | `id_horario` |
| turma | turma | `id_turma` |
| leciona | leciona | (`id_turma`, `mat_professor`) |
| alocacao | alocacao | (`id_turma`, `id_horario`) |
| cursa | cursa | (`mat_estudante`, `id_turma`) |

Os campos multivalorados `email` e `telefone` são arrays no documento
`usuario`. Os relacionamentos são representados por CPF, matrícula, códigos e
identificadores. As quatro coleções do CRUD permanecem canônicas e separadas,
evitando duplicação de dados embutidos.

## CRUD obrigatório

A aplicação implementa Create, Read, Update e Delete de:

- `usuario`;
- `estudante`;
- `vinculo`;
- `curso`.

Também existe o fluxo `/admissoes/nova`, que cadastra usuário, estudante e
vínculo em uma transação real no Atlas.

As regras confirmadas incluem:

- unicidade de CPF e login;
- unicidade de matrícula;
- unicidade do identificador e da combinação estudante/curso em vínculo;
- unicidade do identificador e da combinação acadêmica de curso;
- existência de usuário antes do cadastro de estudante;
- existência de estudante e curso antes do cadastro de vínculo;
- bloqueio da exclusão de estudante ou curso referenciado;
- exclusão individual de vínculo sem remover estudante ou curso;
- rollback da admissão conjunta sem documentos parciais;
- remoção da senha dos retornos públicos e do HTML.

Validators controlam tipos BSON, tamanhos, campos obrigatórios e domínios. Os
índices únicos garantem as principais restrições de chave no banco real. Como o
MongoDB não oferece foreign keys entre coleções, a integridade referencial é
verificada pelo ETL e pela camada de serviços.

## Preparação do ambiente

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

No Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Configuração do `.env`

Crie `.env` localmente com valores próprios:

```dotenv
MONGODB_MODE=atlas
MONGODB_URI=<URI_DO_MONGODB_ATLAS>
MONGODB_DATABASE=<NOME_DO_DATABASE>
DEMO_SEED=0
FLASK_SECRET_KEY=<CHAVE_LOCAL>
```

O arquivo `.env` está ignorado pelo Git e não deve ser versionado, compartilhado
ou incluído em capturas. Nunca registre URI, usuário, senha ou chave secreta no
código-fonte.

## Execução da aplicação

### Modo mock

Executa completamente em memória e não abre conexão de rede:

```bash
MONGODB_MODE=mock python3 -m flask --app app run --debug
```

Seed opcional exclusivo do mock:

```bash
MONGODB_MODE=mock DEMO_SEED=1 python3 -m flask --app app run --debug
```

### Modo Atlas

Usa PyMongo e as configurações locais do `.env`:

```bash
MONGODB_MODE=atlas python3 -m flask --app app run
```

Não existe fallback automático para Atlas. Credenciais e database são exigidos
explicitamente no modo real.

## Testes automatizados

```bash
python3 -m unittest discover -s tests -v
```

Resultado final confirmado:

```text
Ran 32 tests

OK
```

## Setup do MongoDB

Dry-run offline:

```bash
python3 setup_banco.py --dry-run
```

Aplicação real das 16 coleções, validators e índices:

```bash
MONGODB_MODE=atlas python3 setup_banco.py --apply
```

O setup não insere exemplos nem remove documentos ou duplicidades.

## ETL do dump SQL

Dry-run com validação de campos, tipos, duplicidades e referências:

```bash
python3 ETL.py --input universidade-dump-engdados.sql --dry-run
```

Carga real no Atlas:

```bash
MONGODB_MODE=atlas python3 ETL.py --input universidade-dump-engdados.sql --apply
```

O ETL usa upsert pela chave principal e não exclui documentos. O resultado
confirmado foi de 238 registros lidos e válidos, sem inválidos, duplicidades ou
referências ausentes.

## Resultado final

- aplicação Flask conectada ao Atlas;
- cluster MongoDB hospedado na AWS;
- 16 coleções confirmadas;
- validators e índices aplicados;
- ETL com 238 registros válidos;
- CRUD real das quatro estruturas aprovado;
- duplicidades e exclusões referenciais bloqueadas;
- exclusão individual de vínculo aprovada;
- admissão conjunta e rollback real aprovados;
- 32 testes automatizados aprovados;
- registros descartáveis removidos, com `CLEANUP_REMAINING=0`.
