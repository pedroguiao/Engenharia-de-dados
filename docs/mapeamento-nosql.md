# Mapeamento relacional para MongoDB

## Decisão de modelagem

MongoDB foi escolhido por ser o SGBD NoSQL exigido na Parte 2 e por oferecer
documentos BSON, validators JSON Schema, índices únicos e implantação gerenciada
em infraestrutura AWS por meio do Atlas. A hospedagem real do cluster ainda
precisa ser confirmada antes de qualquer operação remota.

Cada tabela SQL é uma coleção canônica independente. Essa escolha mantém as
identidades relacionais, facilita CRUD separado de `usuario`, `estudante`,
`vinculo` e `curso`, evita cópias divergentes de usuários e permite demonstrar
com clareza chaves e referências. Somente arrays naturais de um usuário, como
`email` e `telefone`, permanecem dentro do documento.

Datas são representadas como BSON Date. Literais numéricos decimais são
preservados sem conversão intermediária para `float` e serão enviados como
Decimal128. CPF é armazenado como string de até 13 dígitos para preservar sua
natureza identificadora. Matrículas são strings de até 7 caracteres.

## Coleções e exemplos

Os exemplos usam Extended JSON apenas para tornar datas e decimais visíveis.

### `usuario`

```json
{"cpf":"22222222201","nome":"Pessoa Exemplo","data_nascimento":{"$date":"1990-03-05T00:00:00Z"},"email":["pessoa@example.org"],"telefone":null,"login":"pessoa","senha":"<não exibir>"}
```

PK: `cpf`. Única: `login` quando não nulo. `nome` é obrigatório; tamanhos
máximos seguem o SQL.

### `professor`

```json
{"mat_professor":"P100","cpf":"11111111100","departamento":"DCOMP","formacao":"Doutorado","data_admissao":null,"tipo_jornada_trabalho":"20h","salario":{"$numberDecimal":"2000"}}
```

PK: `mat_professor`. Única: `cpf` quando não nulo. Referências: `cpf` →
`usuario.cpf`; `departamento` → `departamento.cod_depto`. Domínios de formação
e jornada são enums.

### `departamento`

```json
{"cod_depto":"DCOMP","nome":"Departamento de Computação","chefe":"P100","orcamento":{"$numberDecimal":"10000"},"comissal":{"$numberDecimal":"1000"}}
```

PK: `cod_depto`. `nome` é obrigatório. `chefe` referencia
`professor.mat_professor`. O orçamento, quando informado, deve ser maior que
zero.

### `curso`

```json
{"idCurso":1,"nome":"Ciência da Computação","grau":"Bacharelado","turno":"Vespertino","campus":"São Cristóvão","nivel":"Graduação"}
```

PK: `idCurso`. Única composta: `(nome, turno, campus, nivel)` quando todos os
campos estão preenchidos. `nome` e `turno` são obrigatórios; grau, turno e nível
usam os enums SQL.

### `estudante`

```json
{"mat_estudante":"E101","cpf":"22222222201","MC":{"$numberDecimal":"7.0"},"ano_ingresso":2021}
```

PK: `mat_estudante`. Única: `cpf` quando não nulo. `cpf` referencia
`usuario.cpf`. Não há usuário nem vínculos embutidos.

### `vinculo`

```json
{"idVinculo":1,"mat_estudante":"E101","idCurso":3,"data_entrada":null,"status":"Ativo","data_saida":null}
```

PK: `idVinculo`. A aplicação acrescenta unicidade composta de
`(mat_estudante, idCurso)` para impedir dois vínculos do mesmo estudante com o
mesmo curso. Referências: `mat_estudante` → `estudante.mat_estudante` e
`idCurso` → `curso.idCurso`. Status usa o enum SQL.

### `projeto`

```json
{"id_projeto":1,"descricao":"Projeto 1"}
```

PK: `id_projeto`.

### `plano`

```json
{"id_projeto":1,"mat_professor":"P100","mat_estudante":"E103","ano":2018}
```

PK composta: `(mat_estudante, ano)`. Referencia `projeto`, `professor` e
`estudante` por suas respectivas chaves.

### `disciplina`

```json
{"cod_disc":"COMP0198","nome":"Programação Orientada a Objetos","pre_req":"COMP0197","creditos":4,"depto_responsavel":"DCOMP"}
```

PK: `cod_disc`. `nome` é obrigatório. `pre_req` é autorreferência a
`disciplina.cod_disc`; `depto_responsavel` referencia departamento. Créditos
devem estar entre 1 e 11.

### `semestre`

```json
{"ano":2019,"semestre":1,"data_inicio":null,"data_fom":null}
```

PK composta: `(ano, semestre)`. O nome `data_fom` foi preservado porque é o nome
definido no dump, embora provavelmente seja um erro de digitação de `data_fim`.

### `sala`

```json
{"id_sala":1,"descricao":"Sala 101"}
```

PK: `id_sala`.

### `horario`

```json
{"id_horario":1,"dia":"Segunda-feira","slot":1}
```

PK: `id_horario`. `dia` e `slot` são obrigatórios.

### `turma`

```json
{"id_turma":1,"cod_disc":"COMP0212","numero":1,"ano":2017,"semestre":2}
```

PK: `id_turma`. Única composta: `(cod_disc, numero, semestre, ano)` quando os
campos opcionais estão preenchidos. `cod_disc` referencia disciplina;
`(ano, semestre)` referencia semestre.

### `leciona`

```json
{"id_turma":1,"mat_professor":"P100"}
```

PK composta: `(id_turma, mat_professor)`. Ambos são obrigatórios e referenciam
`turma` e `professor`.

### `alocacao`

```json
{"id_turma":1,"id_horario":1,"id_sala":1}
```

PK composta: `(id_turma, id_horario)`. Única composta:
`(id_horario, id_sala)` quando `id_sala` não é nulo. As referências às coleções
`turma`, `horario` e `sala` são inferidas pelo significado das colunas; o dump
não declara foreign keys para essa tabela.

### `cursa`

```json
{"mat_estudante":"E101","id_turma":2,"nota":{"$numberDecimal":"10.0"}}
```

PK composta: `(mat_estudante, id_turma)`. Referencia `estudante` e `turma`;
`nota` é opcional.

## Mapeamento de nomes

| Tabela SQL | Coleção | Alterações de campo |
|---|---|---|
| usuario | usuario | nenhuma |
| professor | professor | nenhuma; `cpf` é referência, não embedding |
| departamento | departamento | nenhuma |
| curso | curso | `idCurso` preservado no documento |
| estudante | estudante | `MC` preservado; `cpf` é referência |
| vinculo | vinculo | SQL `curso` é documentado como `idCurso` |
| projeto | projeto | nenhuma |
| plano | plano | nenhuma |
| disciplina | disciplina | nenhuma |
| semestre | semestre | `data_fom` preservado |
| sala | sala | nenhuma |
| horario | horario | nenhuma |
| turma | turma | nenhuma |
| leciona | leciona | nenhuma |
| alocacao | alocacao | nenhuma |
| cursa | cursa | nenhuma |

## Restrições e limitações

Os validators aplicam tipos, nulabilidade, limites de tamanho, enums e os CHECKs
de orçamento e créditos. Índices únicos reproduzem chaves primárias, chaves
compostas e unicidades declaradas. Para campos `UNIQUE` anuláveis, índices
parciais evitam que MongoDB trate todos os documentos nulos como uma única chave.

MongoDB não possui foreign keys automáticas. Os metadados de referência em
`schemas_mongodb.py` permitem que o ETL detecte referências ausentes, mas não
impedem alterações futuras diretamente no banco. A aplicação CRUD deverá:

1. verificar a existência dos documentos referenciados antes de insert/update;
2. verificar dependentes antes de delete;
3. reproduzir as políticas SQL de CASCADE, SET NULL e NO ACTION;
4. usar transações quando uma operação modificar mais de uma coleção;
5. tratar erros de índice único e validator.

## CRUD local e integridade da aplicação

A aplicação Flask mantém `usuario`, `estudante`, `vinculo` e `curso` separados e
oferece cadastro, listagem, ficha, edição e exclusão individual. A camada de
serviço valida CPF, matrícula, IDs, datas, números, limites, enums, unicidades e
referências antes de acessar os repositórios. Exclusões de usuário, estudante e
curso são bloqueadas quando deixariam referências órfãs.

O fluxo de admissão valida usuário, estudante e vínculo antes da primeira
escrita. Em `mongomock`, um snapshot das quatro coleções permite rollback. O
repositório também aceita uma fábrica de transações para uma futura sessão real
do PyMongo, que ainda precisará ser implementada e homologada no Atlas.

O campo `senha` continua com o tipo e limite definidos no dump. Ele não é
incluído em respostas públicas, páginas, logs ou mensagens; senha vazia em uma
edição mantém o valor anterior. O sistema ainda não implementa autenticação.
Adotar hash de senha exigirá ampliar ou substituir o limite de 32 caracteres e
migrar os documentos, portanto essa mudança não foi feita implicitamente.

O modo web atual aceita apenas `MONGODB_MODE=mock`. A interface e os testes não
abrem conexão de rede. Integração Atlas, transações reais e validação dos dados
remotos permanecem etapas futuras sujeitas a autorização.
