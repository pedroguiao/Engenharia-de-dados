# Parte 2 — CRUD NoSQL com MongoDB

## 1. Identificação

**Disciplina:** Engenharia de Dados

**Professor:** André Britto de Carvalho

**Integrantes:** Allan Gustavo, Pedro Guilherme e Théo Enderson

**Repositório:** https://github.com/pedroguiao/Engenharia-de-dados

## 2. Objetivo

A Parte 2 do Trabalho Prático tem como objetivo mapear para um banco NoSQL todas
as tabelas do modelo relacional da universidade, representar as restrições de
chave, domínio, integridade referencial e `NOT NULL`, e implementar o CRUD das
estruturas correspondentes a `usuario`, `estudante`, `vinculo` e `curso`.

O resultado é uma aplicação Flask conectada a um cluster MongoDB Atlas hospedado
na AWS, contendo todas as estruturas do esquema relacional e operações reais de
inserção, consulta, atualização e exclusão.

## 3. Escolha do MongoDB

O MongoDB foi escolhido por sua representação orientada a documentos, suporte a
arrays e tipos BSON, validators baseados em JSON Schema, índices únicos,
consultas por campos e transações entre múltiplos documentos.

Os campos multivalorados `email` e `telefone` são representados naturalmente
como arrays. As chaves e relacionamentos são preservados por campos como CPF,
matrícula, códigos e identificadores. As quatro estruturas do CRUD permanecem em
coleções canônicas separadas, evitando cópias embutidas que precisariam ser
sincronizadas.

Para desenvolvimento e testes locais foi utilizado `mongomock`. A execução real
usa PyMongo e MongoDB Atlas.

## 4. Modelagem das 16 coleções

Todas as tabelas relacionais foram representadas por coleções MongoDB:

| Tabela relacional | Coleção | Chave principal | Referências |
|---|---|---|---|
| usuario | usuario | `cpf` | — |
| professor | professor | `mat_professor` | usuario; departamento |
| departamento | departamento | `cod_depto` | professor chefe |
| curso | curso | `idCurso` | — |
| estudante | estudante | `mat_estudante` | usuario |
| vinculo | vinculo | `idVinculo` | estudante; curso |
| projeto | projeto | `id_projeto` | — |
| plano | plano | (`mat_estudante`, `ano`) | projeto; professor; estudante |
| disciplina | disciplina | `cod_disc` | pré-requisito; departamento |
| semestre | semestre | (`ano`, `semestre`) | — |
| sala | sala | `id_sala` | — |
| horario | horario | `id_horario` | — |
| turma | turma | `id_turma` | disciplina; semestre |
| leciona | leciona | (`id_turma`, `mat_professor`) | turma; professor |
| alocacao | alocacao | (`id_turma`, `id_horario`) | turma; horário; sala¹ |
| cursa | cursa | (`mat_estudante`, `id_turma`) | estudante; turma |

¹ As referências de `alocacao` foram inferidas pelo significado dos campos; o
dump SQL não declara foreign keys para essa tabela.

### 4.1 Estruturas principais do CRUD

`usuario` armazena CPF, nome, data de nascimento, arrays de e-mail e telefone,
login e senha. A senha é persistida conforme o schema de origem, mas não é
retornada pelos serviços nem renderizada pela interface.

`estudante` armazena matrícula, CPF do usuário, média de conclusão e ano de
ingresso. O CPF referencia um documento existente em `usuario`.

`curso` armazena identificador, nome, grau, turno, campus e nível.

`vinculo` relaciona estudante e curso, mantendo identificador, matrícula,
identificador do curso, datas de entrada e saída e status.

## 5. Validators, índices e restrições

As 16 coleções possuem validators definidos em `schemas_mongodb.py`. Eles
controlam:

- tipos BSON;
- tamanhos máximos de strings;
- campos obrigatórios;
- domínios de formação, jornada, grau, turno, nível e status;
- limites numéricos declarados no modelo;
- formato textual de CPF e matrícula;
- rejeição de campos não previstos no documento.

Os índices únicos representam as chaves principais e demais restrições de
unicidade. Entre os índices confirmados estão:

- CPF e login únicos em `usuario`;
- matrícula e CPF únicos em `estudante`;
- identificador e combinação acadêmica únicos em `curso`;
- identificador e combinação estudante/curso únicos em `vinculo`;
- índices de consulta de vínculo por estudante e curso;
- chaves simples ou compostas das demais coleções.

O MongoDB não possui foreign keys automáticas entre coleções. Por isso, a
integridade referencial é verificada em duas etapas:

1. o ETL valida todas as referências antes da carga;
2. a camada de serviços verifica referências antes das operações do CRUD.

As exclusões que deixariam estudante ou curso órfão são bloqueadas. A exclusão
de um vínculo remove somente o documento do vínculo, preservando os documentos
de estudante e curso.

## 6. Arquitetura da aplicação

```text
Interface Flask → serviços → repositórios → MongoDB
```

| Componente | Responsabilidade |
|---|---|
| `app.py` | Rotas, formulários, templates e seleção dos modos mock/Atlas |
| `config.py` | Leitura segura do `.env` e validação das configurações |
| `db.py` | Criação dos clientes mongomock e PyMongo |
| `repositories.py` | Consultas, inserções, atualizações, exclusões e sessões |
| `services.py` | Regras de domínio, CRUD, duplicidades, referências e transação |
| `schemas_mongodb.py` | Validators, índices, chaves e referências das 16 coleções |
| `setup_banco.py` | Aplicação das coleções, validators e índices |
| `ETL.py` | Parser do dump, conversão de tipos, validação e carga |
| `templates/` e `static/` | Interface web responsiva |
| `tests/` | Testes automatizados offline |

`MONGODB_MODE=mock` cria um banco em memória sem conexão de rede.
`MONGODB_MODE=atlas` exige configuração explícita, cria um cliente PyMongo e
valida a conexão real. Não existe fallback automático para Atlas.

## 7. Setup do banco

`setup_banco.py` trabalha em dry-run por padrão. Nesse modo, apenas mostra o
plano das 16 coleções, validators e índices, sem abrir conexão ou alterar o
banco.

Com `--apply`, o script conecta ao Atlas, cria as coleções ausentes, atualiza
validators das coleções existentes e confirma os índices definidos. Ele não
insere dados de demonstração, não remove duplicidades e não exclui documentos.

Na validação final, as 16 coleções, validators e índices já estavam aplicados no
Atlas.

## 8. ETL do dump SQL

`ETL.py` lê `universidade-dump-engdados.sql`, reconhece comandos que ocupam
várias linhas e processa:

- valores `NULL`;
- strings com vírgulas, apóstrofos e ponto e vírgula;
- arrays PostgreSQL;
- datas;
- inteiros e decimais;
- colunas explícitas ou posicionais;
- atualizações de chefia dos departamentos.

Antes da escrita, o ETL verifica validators, chaves únicas e referências. A
carga real usa upsert pela chave principal e não exclui documentos existentes.

### 8.1 Resultado do ETL

| Coleção | Lidos | Válidos | Inválidos | Duplicados | Referências ausentes |
|---|---:|---:|---:|---:|---:|
| usuario | 28 | 28 | 0 | 0 | 0 |
| professor | 15 | 15 | 0 | 0 | 0 |
| departamento | 6 | 6 | 0 | 0 | 0 |
| curso | 5 | 5 | 0 | 0 | 0 |
| estudante | 13 | 13 | 0 | 0 | 0 |
| vinculo | 13 | 13 | 0 | 0 | 0 |
| projeto | 5 | 5 | 0 | 0 | 0 |
| plano | 6 | 6 | 0 | 0 | 0 |
| disciplina | 19 | 19 | 0 | 0 | 0 |
| semestre | 2 | 2 | 0 | 0 | 0 |
| sala | 0 | 0 | 0 | 0 | 0 |
| horario | 0 | 0 | 0 | 0 | 0 |
| turma | 27 | 27 | 0 | 0 | 0 |
| leciona | 22 | 22 | 0 | 0 | 0 |
| alocacao | 0 | 0 | 0 | 0 | 0 |
| cursa | 77 | 77 | 0 | 0 | 0 |
| **Total** | **238** | **238** | **0** | **0** | **0** |

Também foram processadas quatro atualizações de chefia. O resultado confirmou
238 registros válidos, sem inconsistências bloqueantes.

## 9. CRUD das quatro estruturas

### 9.1 Usuario

- Create cadastra CPF, nome, data, contatos, login e senha;
- Read lista usuários e consulta a ficha sem expor a senha;
- Update altera os campos permitidos, mantendo o CPF imutável;
- Delete remove o usuário quando não existe estudante relacionado;
- CPF e login duplicados são rejeitados.

### 9.2 Estudante

- Create exige usuário existente e matrícula disponível;
- Read consulta matrícula, usuário e vínculos relacionados;
- Update altera CPF referenciado, média e ano, mantendo a matrícula;
- Delete remove o estudante somente quando não existem vínculos;
- matrícula e associação duplicada de CPF são rejeitadas.

### 9.3 Curso

- Create gera o identificador e cadastra os dados acadêmicos;
- Read lista e consulta os dados do curso;
- Update altera nome, grau, turno, campus e nível, mantendo o ID;
- Delete remove somente cursos sem vínculos;
- combinações acadêmicas duplicadas são rejeitadas.

### 9.4 Vinculo

- Create exige estudante e curso existentes;
- Read consulta vínculo, estudante, curso, datas e status;
- Update altera referências, datas e status, mantendo o ID;
- Delete remove somente o vínculo selecionado;
- a combinação estudante/curso duplicada é rejeitada.

## 10. Efeito dos métodos no banco

As operações foram executadas com registros descartáveis identificados para a
validação final e confirmadas diretamente no MongoDB Atlas:

- **Create:** um novo documento foi inserido e localizado no Atlas para cada uma
  das quatro coleções do CRUD;
- **Read:** os documentos foram consultados pela aplicação, sem exposição do
  campo de senha;
- **Update:** os campos permitidos foram alterados e os novos valores foram
  confirmados nos documentos persistidos;
- **Delete:** os documentos foram removidos e sua ausência foi confirmada no
  banco;
- a exclusão individual de vínculo removeu somente o vínculo, mantendo
  estudante e curso;
- a exclusão de curso e estudante referenciados foi bloqueada;
- duplicidades de CPF, login, matrícula, curso e vínculo foram rejeitadas pelos
  serviços e índices;
- uma falha por duplicidade durante a admissão conjunta abortou a transação sem
  deixar documentos parciais.

Essas operações serão demonstradas ao vivo na apresentação, conforme a exigência
do trabalho de mostrar o efeito de cada método no banco de dados.

## 11. Admissão conjunta e transação

A rota `/admissoes/nova` cadastra usuário, estudante e vínculo inicial em um
único fluxo. No Atlas, o repositório abre uma sessão PyMongo e inicia uma
transação real.

No teste de sucesso, os três documentos foram inseridos e consultados. No teste
de falha, uma duplicidade foi provocada na terceira inserção. A exceção abortou a
transação e foi confirmada a ausência do usuário e do estudante parciais.

Ao final da validação, todos os registros descartáveis foram removidos na ordem
vínculo, estudante, usuário e curso. O resultado final foi
`CLEANUP_REMAINING=0`.

## 12. Testes

### 12.1 Testes automatizados

Foram executados 32 testes automatizados, todos aprovados. A suíte cobre:

- CRUD das quatro estruturas;
- duplicidades;
- validações de domínio e campos opcionais;
- referências inexistentes;
- bloqueios de exclusão;
- exclusão individual de vínculo;
- senha ausente dos retornos e do HTML;
- admissão conjunta e rollback;
- rotas Flask e páginas de erro;
- modo mock sem conexão de rede;
- parser SQL, 16 coleções, duplicidades e referências do ETL.

Resultado confirmado:

```text
Ran 32 tests

OK
```

### 12.2 Testes reais no Atlas

No cluster MongoDB Atlas hospedado na AWS foram confirmados:

- conexão real da aplicação por PyMongo;
- presença das 16 coleções;
- validators e índices;
- carga dos 238 registros válidos;
- CRUD de `usuario`, `estudante`, `curso` e `vinculo`;
- bloqueios de duplicidade e integridade;
- exclusão individual de vínculo;
- admissão conjunta com transação real;
- rollback sem documentos parciais;
- limpeza completa dos registros descartáveis.

## 13. Contagens finais no Atlas

| Coleção | Documentos |
|---|---:|
| usuario | 29 |
| professor | 15 |
| departamento | 6 |
| curso | 5 |
| estudante | 14 |
| vinculo | 14 |
| projeto | 5 |
| plano | 6 |
| disciplina | 19 |
| semestre | 2 |
| sala | 0 |
| horario | 0 |
| turma | 27 |
| leciona | 22 |
| alocacao | 0 |
| cursa | 77 |

`usuario`, `estudante` e `vinculo` possuem um documento adicional em relação ao
dump. Esses três registros já existiam antes da validação final e não foram
alterados pelos testes descartáveis.

## 14. Conclusão

A Parte 2 foi concluída com o mapeamento das 16 tabelas para MongoDB, aplicação
dos validators e índices, carga ETL de 238 registros válidos e implementação do
CRUD real das quatro estruturas obrigatórias.

A aplicação Flask foi validada no MongoDB Atlas hospedado na AWS. As regras de
unicidade e integridade foram confirmadas, as exclusões referenciais foram
bloqueadas, a exclusão individual de vínculo preservou seus documentos
relacionados e a admissão conjunta executou com transação e rollback reais.

Os 32 testes automatizados foram aprovados e os registros descartáveis usados na
validação foram completamente removidos, mantendo inalterados os dados reais do
grupo.
