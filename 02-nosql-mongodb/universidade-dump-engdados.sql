DROP SCHEMA universidade CASCADE;

CREATE SCHEMA universidade;

CREATE DOMAIN universidade.matricula AS VARCHAR(7);

CREATE DOMAIN universidade.tipo_cpf AS NUMERIC(13);

CREATE TABLE universidade.usuario(
	cpf universidade.tipo_cpf,
	nome	VARCHAR(100) NOT NULL,
	data_nascimento DATE,
	email VARCHAR[],
	telefone VARCHAR[],
	login VARCHAR(45) UNIQUE,
	senha VARCHAR(32),
	CONSTRAINT pk_usuario PRIMARY KEY (cpf)
);

CREATE TYPE universidade.tipo_jornada AS ENUM ('20h', '40h', 'DE');
CREATE TYPE universidade.tipo_formacao AS ENUM ('Graduação', 'Especialização', 'Mestrado', 'Doutorado');

CREATE TABLE universidade.professor(
	mat_professor universidade.matricula,
	cpf  universidade.tipo_cpf UNIQUE,
	departamento VARCHAR(5),
	formacao universidade.tipo_formacao,
	data_admissao DATE,
	tipo_jornada_trabalho universidade.tipo_jornada,
	salario FLOAT,
	CONSTRAINT pk_professor PRIMARY KEY(mat_professor),
	CONSTRAINT fk_usuario FOREIGN KEY (cpf) REFERENCES universidade.usuario(cpf)
	ON DELETE SET NULL ON UPDATE CASCADE
);


CREATE TABLE universidade.departamento(
	cod_depto VARCHAR(5),
	nome VARCHAR(50) NOT NULL,
	chefe universidade.matricula,
	orcamento REAL CONSTRAINT ck_orcamento CHECK(orcamento > 0),
	comissal FLOAT,
	CONSTRAINT pk_departamento PRIMARY KEY(cod_depto)
);

ALTER TABLE universidade.professor ADD 
CONSTRAINT fk_alocacao FOREIGN KEY (departamento) REFERENCES universidade.departamento(cod_depto)
ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE universidade.departamento ADD 
CONSTRAINT fk_chefia FOREIGN KEY (chefe) REFERENCES universidade.professor(mat_professor)
ON DELETE SET NULL ON UPDATE CASCADE;

CREATE TYPE universidade.tipo_grau AS ENUM ('Bacharelado', 'Licenciatura Plena');
CREATE TYPE universidade.tipo_nivel AS ENUM ('Graduação', 'Mestrado', 'Doutorado', 'Lato');
CREATE TYPE universidade.tipo_turno AS ENUM ('Matutino', 'Vespertino', 'Noturno', 'Turno Indefinido');

CREATE TABLE universidade.curso(
	idCurso SERIAL PRIMARY KEY,
	nome VARCHAR(100) NOT NULL,
	grau universidade.tipo_grau,
	turno universidade.tipo_turno NOT NULL,
	campus VARCHAR(100),
	nivel universidade.tipo_nivel,
	CONSTRAINT uq_curso UNIQUE(nome, turno, campus, nivel)

);

CREATE TYPE universidade.status_estudante AS ENUM ('Ativo', 'Cancelada', 'Formando', 'Graduado');

CREATE TABLE universidade.estudante(
	mat_estudante universidade.matricula,
	cpf  universidade.tipo_cpf ,
	MC DECIMAL(2),
	ano_ingresso INT,

	CONSTRAINT pk_estudante PRIMARY KEY(mat_estudante),
	CONSTRAINT fk_usuario FOREIGN KEY (cpf) REFERENCES universidade.usuario(cpf)
	ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT uq_cpf UNIQUE(cpf)
	
);

CREATE TABLE universidade.vinculo(
	idVinculo SERIAL PRIMARY KEY,
	mat_estudante universidade.matricula,
	curso INT,
	data_entrada DATE,
	status universidade.status_estudante,
	data_saida DATE,
	CONSTRAINT fk_curso FOREIGN KEY (curso) REFERENCES universidade.curso(idCurso)
	ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_estudabte FOREIGN KEY (mat_estudante) REFERENCES universidade.estudante(mat_estudante)
	ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE universidade.projeto(
	id_projeto INT,
	descricao VARCHAR,
	CONSTRAINT pk_projeto PRIMARY KEY(id_projeto)
);

CREATE TABLE universidade.plano(
	id_projeto INT,
	mat_professor universidade.matricula,
	mat_estudante universidade.matricula,
	ano INT,
	CONSTRAINT pk_plano PRIMARY KEY(mat_estudante, ano),
	CONSTRAINT fk_projeto FOREIGN KEY (id_projeto) REFERENCES universidade.projeto(id_projeto) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_professor FOREIGN KEY (mat_professor) REFERENCES universidade.professor(mat_professor) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_mat_estudante FOREIGN KEY (mat_estudante) REFERENCES universidade.estudante(mat_estudante) ON DELETE SET NULL ON UPDATE CASCADE
);



CREATE TABLE universidade.disciplina(
	cod_disc VARCHAR(8),
	nome	VARCHAR(40) NOT NULL,
	pre_req VARCHAR(8),
	creditos SMALLINT CONSTRAINT  ck_creditos CHECK (1<=creditos AND creditos < 12),
	depto_responsavel VARCHAR(5),
	CONSTRAINT pk_disciplina PRIMARY KEY (cod_disc),
	CONSTRAINT fk_pre_req FOREIGN KEY(pre_req) REFERENCES universidade.disciplina(cod_disc)
	ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT fk_responsavel FOREIGN KEY(depto_responsavel) REFERENCES universidade.departamento(cod_depto)
	ON DELETE SET NULL ON UPDATE CASCADE
);


CREATE SEQUENCE universidade.seq_turma INCREMENT 1 START 1;

CREATE TABLE universidade.semestre(
	ano SMALLINT,
	semestre SMALLINT,
	data_inicio DATE,
	data_fom DATE,
	CONSTRAINT pk_semestre PRIMARY KEY (ano, semestre)
);

CREATE TABLE universidade.sala(
	id_sala SERIAL,
	descricao VARCHAR,
	CONSTRAINT pk_sala PRIMARY KEY (id_sala)
);


CREATE TABLE universidade.horario(
	id_horario SERIAL,
	dia VARCHAR(15) NOT NULL,
	slot  SMALLINT NOT NULL,
	CONSTRAINT pk_horario PRIMARY KEY (id_horario)
);


CREATE TABLE universidade.turma(
	id_turma INT DEFAULT nextval('universidade.seq_turma'),
	cod_disc VARCHAR(8) NOT NULL,
	numero INT,
	ano SMALLINT,
	semestre SMALLINT,
	CONSTRAINT pk_turma PRIMARY KEY(id_turma),
	CONSTRAINT uq_turma UNIQUE(cod_disc, numero, semestre, ano),
	CONSTRAINT fk_disciplina FOREIGN KEY(cod_disc) REFERENCES universidade.disciplina(cod_disc)
	ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_semestre FOREIGN KEY(ano, semestre) REFERENCES universidade.semestre(ano,semestre)
	ON DELETE NO ACTION ON UPDATE CASCADE
);

CREATE TABLE universidade.leciona(
	id_turma INT NOT NULL,
	mat_professor universidade.matricula NOT NULL,
	CONSTRAINT pk_leciona PRIMARY KEY (id_turma, mat_professor),
	CONSTRAINT fk_turma FOREIGN KEY (id_turma) REFERENCES universidade.turma(id_turma) ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_professor FOREIGN KEY (mat_professor) REFERENCES universidade.professor(mat_professor) ON DELETE  CASCADE ON UPDATE CASCADE
);

CREATE TABLE universidade.alocacao(
	id_turma INT,
	id_horario INT,
	id_sala INT,
	CONSTRAINT pk_alocacao PRIMARY KEY (id_turma, id_horario),
	CONSTRAINT uq_alocacao UNIQUE(id_horario, id_sala)
);

CREATE TABLE universidade.cursa(
	mat_estudante universidade.matricula,
	id_turma INT,
	nota	REAL,
	CONSTRAINT pk_cursa PRIMARY KEY(mat_estudante, id_turma),
	CONSTRAINT fk_turma FOREIGN KEY(id_turma) REFERENCES universidade.turma(id_turma)
	ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT fk_estudante FOREIGN KEY(mat_estudante) REFERENCES universidade.estudante(mat_estudante)
	ON DELETE CASCADE ON UPDATE CASCADE
);



INSERT INTO universidade.departamento VALUES ('DCOMP', 'Departamento de Computação', NULL, 10000,1000);
INSERT INTO universidade.departamento VALUES ('DCOM2', 'Departamento de Computação', NULL, 5000,0);
INSERT INTO universidade.departamento VALUES ('DMA', 'Departamento de Matemática', NULL, 20000,1000);
INSERT INTO universidade.departamento VALUES ('DFI', 'Departamento de Física', NULL, 50000,1000);
INSERT INTO universidade.departamento VALUES ('DECAT', 'Departamento de Estatística e Ciências Atuarias', NULL, 10000,1000);
insert into universidade.departamento values ('DEL' , 'Departamento de Engenharia Elétrica', NULL, NULL,0);

INSERT INTO universidade.usuario VALUES ('11111111100', 'Prof A', '1980/03/05', '{"profA@email.com"}', '{"99998888","88889999"}','profa','senha1');
INSERT INTO universidade.professor VALUES ('P100', '11111111100', 'DCOMP','Doutorado',NULL,'20h', 2000);


INSERT INTO universidade.usuario
    VALUES ('11111111101', 'Prof B', '1980/07/23', '{"profB@email.com", "pB@mail.com"}', NULL, 'profb', 'senha2');
INSERT INTO universidade.professor VALUES ('P200', '11111111101','DCOMP','Doutorado',NULL,'20h', 2000);


INSERT INTO universidade.usuario
    VALUES ('11111111102', 'Prof C', '1987/05/12', '{"profc@email.com"}', '{"99998885","84389999"}', 'profc','senha3');
INSERT INTO universidade.professor VALUES ('P300', '11111111102', 'DCOMP','Doutorado',NULL,'40h', 4000);


INSERT INTO universidade.usuario
    VALUES ('11111111103', 'Prof D', '1975/01/22', NULL, NULL, 'profd', 'senha4');
INSERT INTO universidade.professor VALUES ('P400', '11111111103', 'DCOMP','Mestrado',NULL,'20h', 2000);



INSERT INTO universidade.usuario
    VALUES ('11111111104', 'Prof E', '1980/04/25', '{"profE@email.com"}', '{"99298888","88889999"}', 'profe','senha5');
INSERT INTO universidade.professor VALUES ('P500', '11111111104', 'DCOMP','Mestrado',NULL,'40h', 4000);

INSERT INTO universidade.usuario
    VALUES ('11111111105', 'Prof F','1960/03/05', '{"profF@email.com"}', '{"89998888","98889999"}', 'proff','senha6');
INSERT INTO universidade.professor VALUES ('P600', '11111111105', 'DMA','Especialização',NULL,'20h', 1500);


INSERT INTO universidade.usuario
    VALUES ('11111111106', 'Prof G','1981/03/05', '{"profG@email.com"}', '{"99978888","86889999"}', 'profg','senha7');
INSERT INTO universidade.professor VALUES ('P700', '11111111106', 'DFI','Mestrado',NULL,'40h', 4000);


INSERT INTO universidade.usuario
    VALUES ('11111111107', 'Prof H','1972/08/3', '{"profh@email.com"}', '{"90998888","88889999"}', 'profh', 'senha8');
INSERT INTO universidade.professor VALUES ('P800', '11111111107', 'DCOMP','Mestrado',NULL,'40h', 2000);


INSERT INTO universidade.usuario
    VALUES ('11111111108', 'Prof A', '1986/04/01', '{"profA2@email.com"}', '{"90998088","81889999"}', 'profam', 'senha9');
INSERT INTO universidade.professor VALUES('P900', '11111111108', 'DCOMP','Mestrado',NULL,'DE', 2000);


INSERT INTO universidade.usuario
    VALUES ('11111111109', 'Prof I', '1980/03/05', '{"profI@email.com"}', NULL, 'profi', 'sennha10');
INSERT INTO universidade.professor VALUES('P1000', '11111111109', 'DCOMP','Doutorado',NULL,'DE', 6000);


INSERT INTO universidade.usuario
    VALUES ('11111111110', 'Prof F', '1981/09/05', '{"profFF@email.com"}', '{"99668888","88329999"}','proffd', 'senha12');
INSERT INTO universidade.professor VALUES('P1100', '11111111110', 'DECAT','Graduação',NULL,'20h', 1000);


INSERT INTO universidade.usuario
    VALUES ('11111111111', 'Prof K', '1980/03/04', '{"profK@email.com"}', '{"79998888","97889999"}', 'profk','senha11');
INSERT INTO universidade.professor VALUES('P1200', '11111111111', 'DMA','Mestrado',NULL,'20h', 2000);


INSERT INTO universidade.usuario
    VALUES ('11111111112', 'Prof I', '1980/03/05', '{"profI@email.com"}', '{"93998888","92889999"}', 'profim','senha13');
INSERT INTO universidade.professor VALUES('P1300', '11111111112', 'DMA','Doutorado',NULL,'20h', 2500);


INSERT INTO universidade.usuario
    VALUES ('11111111113', 'Prof G', '1954/06/15', '{"profGA@email.com"}', '{"97698888","88129999"}', 'profgf', 'senha14');
INSERT INTO universidade.professor VALUES ('P1400', '11111111113', 'DFI','Doutorado',NULL,'40h', 4000);


INSERT INTO universidade.usuario
    VALUES ('11111111114', 'Prof P', '1989/11/05', '{"profP@email.com"}', '{"99128888","88339999"}', 'profp', 'senha15');
INSERT INTO universidade.professor VALUES ('P1500', '11111111114', 'DCOM2','Doutorado',NULL,'DE', 6000);


UPDATE universidade.departamento SET chefe = 'P100' WHERE cod_depto = 'DCOMP';
UPDATE universidade.departamento SET chefe = 'P600' WHERE cod_depto = 'DMA';
UPDATE universidade.departamento SET chefe = 'P1100' WHERE cod_depto = 'DECAT';
UPDATE universidade.departamento SET chefe = 'P1400' WHERE cod_depto = 'DFI';

INSERT INTO universidade.usuario
    VALUES ('22222222201', 'Steve Jobs', '1990/03/05', '{"steve@email.com","steve@apple.com"}', NULL,'steve','s1');
INSERT INTO universidade.estudante VALUES('E101', '22222222201', 7.0,2021);

INSERT INTO universidade.usuario
    VALUES ('22222222202', 'Paul Bell', '1999/09/15', '{bell@email.com}', NULL,'paul','s2');
INSERT INTO universidade.estudante VALUES  ('E102', '22222222202', 8.3,2021);
	
INSERT INTO universidade.usuario
    VALUES ('22222222203', 'Alan Turing', '1912/07/23', NULL,NULL,'alan', 's3');
INSERT INTO universidade.estudante VALUES('E103', '22222222203', 6.7,2021);
	
INSERT INTO universidade.usuario
    VALUES ('22222222204', 'John Hopcroft', '1939/10/07', '{"hopcroft@lfc.com"}',NULL,'john','s4');
INSERT INTO universidade.estudante VALUES('E104', '22222222204',0,2021);
	
INSERT INTO universidade.usuario 
	VALUES ('22222222205', 'Ada Lovelace', '1985/11/27', NULL, NULL,'ada','s5');
INSERT INTO universidade.estudante VALUES('E105', '22222222205',9,2022);
	
INSERT INTO universidade.usuario
    VALUES ('22222222206', 'Grace Hooper', '1996/12/10', '{"hooper@linguagens.com"}',NULL, 'grace','s5');
INSERT INTO universidade.estudante VALUES('E106', '22222222206', 7.7,2022);
	
INSERT INTO universidade.usuario
    VALUES ('22222222207', 'Charles Babbage', '1971/12/26', NULL, NULL,'charles', 's6');
INSERT INTO universidade.estudante VALUES('E107', '22222222207',5.5,2022);
	
INSERT INTO universidade.usuario
    VALUES ('22222222208', 'Musa al-Khwarizmi',  '1950/12/26', NULL, NULL, 'musa', 's7');
INSERT INTO universidade.estudante VALUES('E108', '22222222208', 6.5,2023);
	
INSERT INTO universidade.usuario
    VALUES ('22222222209', 'Cesar Lattes',  '1924/06/11', '{"cesar@cnpq.com", "lattes@curriculo.com"}',NULL, 'lattes', 's8');
INSERT INTO universidade.estudante VALUES('E109', '22222222209', 6.0,2023);
	
INSERT INTO universidade.usuario
    VALUES ('22222222210', 'Donald Knuth', '1938/01/10', '{"knuth@algorithms.com"}',NULL, 'knuth','s9');
INSERT INTO universidade.estudante VALUES('E110', '22222222210', 2.1,2023);
	
INSERT INTO universidade.usuario
    VALUES ('22222222211', 'Abraham Silberschatz',  '1956/01/10', '{"silberchatz@sgbd.com"}',NULL, 'abraham','s10');
INSERT INTO universidade.estudante VALUES('E111', '22222222211',3.3,2023);
	
INSERT INTO universidade.usuario
    VALUES ('22222222212', 'Elmasri Navathe',  '1944/03/24', NULL, NULL,'elmasri', 's11');
INSERT INTO universidade.estudante VALUES('E112', '22222222212', 4.5,2024);
	
INSERT INTO universidade.usuario
    VALUES ('22222222213', 'Ramakrishnam Raghu',  '1965/08/22', NULL, NULL, 'raghu','s12');
INSERT INTO universidade.estudante VALUES('E113', '22222222213', 8.1,2024);

INSERT INTO universidade.curso VALUES (1,'Ciência da Computação', 'Bacharelado', 'Vespertino', 'São Cristóvão', 'Graduação');
INSERT INTO universidade.curso VALUES (2,'Sistemas de Informação', 'Bacharelado', 'Noturno', 'São Cristóvão', 'Graduação');
INSERT INTO universidade.curso VALUES (3,'Sistemas de Informação', 'Bacharelado', 'Matutino', 'Itabaiana', 'Graduação');
INSERT INTO universidade.curso VALUES (4,'Engenharia de Computação', 'Bacharelado', 'Vespertino', 'São Cristóvão', 'Graduação');
INSERT INTO universidade.curso VALUES (5,'Inteligência Artificial', 'Bacharelado', 'Vespertino', 'São Cristóvão', 'Graduação');

INSERT INTO universidade.vinculo VALUES(1, 'E101',3,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(2, 'E102',2,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(3, 'E103',1,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(4, 'E104',4,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(5, 'E105',1,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(6, 'E106',1,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(7, 'E107',1,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(8, 'E108',5,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(9, 'E109',1,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(10, 'E110',5,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(11, 'E111',4,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(12, 'E112',2,NULL, 'Ativo', NULL);
INSERT INTO universidade.vinculo VALUES(13, 'E113',2,NULL, 'Ativo', NULL);


INSERT INTO universidade.projeto VALUES(1 , 'Projeto 1');
INSERT INTO universidade.projeto VALUES(2 , 'Projeto 2');
INSERT INTO universidade.projeto VALUES(3 , 'Projeto 3');
INSERT INTO universidade.projeto VALUES(4 , 'Projeto 4');
INSERT INTO universidade.projeto VALUES(5 , 'Projeto 5');


INSERT INTO universidade.plano VALUES (1, 'P100', 'E103', 2018);
INSERT INTO universidade.plano VALUES (2, 'P200', 'E105', 2018);
INSERT INTO universidade.plano VALUES (3, 'P300', 'E106', 2018);
INSERT INTO universidade.plano VALUES (4, 'P500', 'E107', 2018);
INSERT INTO universidade.plano VALUES (5, 'P600', 'E108', 2018);
INSERT INTO universidade.plano VALUES (1, 'P100', 'E109', 2018);
	

INSERT INTO universidade.disciplina VALUES('COMP0196', 'Fundamentos da Computação', NULL, 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0197', 'Programação Imperativa', NULL, 6, 'DCOMP' );
INSERT INTO universidade.disciplina VALUES('COMP0198', 'Programação Orientada à Objetos', 'COMP0197', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0199', 'Programação Declarativa', 'COMP0197', 4, 'DCOMP');    
INSERT INTO universidade.disciplina VALUES('COMP0212', 'Estrutura de Dados I', 'COMP0197', 6, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0213', 'Estrutura de Dados II', 'COMP0212', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0222', 'Inteligência Artificial', 'COMP0199', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0233', 'Lógica para Computação', NULL, 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0279', 'Desenvolvimento de Software I', 'COMP0197', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0280', 'Desenvolvimento de Software II', 'COMP0279', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0281', 'Desenvolvimento de Software III', 'COMP0280', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES('COMP0298', 'Redes de Computadores', NULL, 4, NULL);
INSERT INTO universidade.disciplina VALUES('COMP0311', 'Banco de dados', 'COMP0213', 4, 'DCOMP');     
INSERT INTO universidade.disciplina VALUES('COMP0326', 'Sistemas Distribuídos', 'COMP0298', 4, 'DCOMP');
INSERT INTO universidade.disciplina VALUES ('MAT0064', 'Cálculo I', NULL, 6, 'DMA');
INSERT INTO universidade.disciplina VALUES ('MAT0065', 'Cálculo II', NULL, 6, 'DMA');
INSERT INTO universidade.disciplina VALUES ('MAT0096', 'Cálculo Numérico', NULL, 4, 'DMA');
INSERT INTO universidade.disciplina VALUES ('FISI0050', 'Física A', NULL, 4, 'DFI');
INSERT INTO universidade.disciplina VALUES ('FISI0051', 'Física B', 'FISI0050', 4, 'DFI');

INSERT INTO universidade.semestre VALUES (2017,2,NULL, NULL);
INSERT INTO universidade.semestre VALUES (2019,1,NULL, NULL);


INSERT INTO universidade.turma VALUES(1,'COMP0212', 1, 2017,2);
INSERT INTO universidade.turma VALUES(2,'COMP0213', 1, 2017,2);
INSERT INTO universidade.turma VALUES(3,'COMP0311', 1, 2017,2);

INSERT INTO universidade.turma VALUES(4, 'COMP0198', 1, 2017,2);
INSERT INTO universidade.turma VALUES(5, 'COMP0199', 1, 2017,2);

INSERT INTO universidade.turma VALUES(6, 'COMP0233', 1, 2017,2);
INSERT INTO universidade.turma VALUES(7, 'COMP0196', 1, 2017,2);
INSERT INTO universidade.turma VALUES(8, 'COMP0197', 1, 2017,2);

INSERT INTO universidade.turma VALUES(9, 'COMP0279',1,  2017,2);
INSERT INTO universidade.turma VALUES(10, 'COMP0280',1, 2017,2);
INSERT INTO universidade.turma VALUES(11, 'COMP0281',1, 2017,2);

INSERT INTO universidade.turma VALUES(12,'COMP0298',1, 2017,2);
INSERT INTO universidade.turma VALUES(13, 'COMP0326',2, 2017,2);

INSERT INTO universidade.turma VALUES(14,'MAT0096',1, 2017,2);
INSERT INTO universidade.turma VALUES(15, 'MAT0064',1, 2017,2);

INSERT INTO universidade.turma VALUES(16,'MAT0096',2, 2017,2);

INSERT INTO universidade.turma VALUES(17, 'MAT0096',3, 2017,2);

INSERT INTO universidade.turma VALUES(18, 'MAT0065',1, 2017,2);

INSERT INTO universidade.turma VALUES(19, 'FISI0050',1, 2017,2);

INSERT INTO universidade.turma VALUES(20, 'COMP0199',2, 2017,2);
INSERT INTO universidade.turma VALUES(21, 'COMP0233',2, 2017,2);
INSERT INTO universidade.turma VALUES(22, 'COMP0222',1, 2017,2);

INSERT INTO universidade.turma VALUES(23, 'MAT0065',1, 2019,1);

INSERT INTO universidade.turma VALUES(24, 'FISI0050',1, 2019,1);

INSERT INTO universidade.turma VALUES(25, 'COMP0199',2, 2019,1);
INSERT INTO universidade.turma VALUES(26, 'COMP0233',2, 2019,1);
INSERT INTO universidade.turma VALUES(27, 'COMP0222',1, 2019,1);


INSERT INTO universidade.leciona VALUES (1,'P100');
INSERT INTO universidade.leciona VALUES (2,'P100');
INSERT INTO universidade.leciona VALUES (3,'P100');
INSERT INTO universidade.leciona VALUES (4,'P200');
INSERT INTO universidade.leciona VALUES (5,'P200');
INSERT INTO universidade.leciona VALUES (6,'P300');
INSERT INTO universidade.leciona VALUES (7,'P300');
INSERT INTO universidade.leciona VALUES (8,'P300');
INSERT INTO universidade.leciona VALUES (9,'P400');
INSERT INTO universidade.leciona VALUES (10,'P400');
INSERT INTO universidade.leciona VALUES (11,'P400');
INSERT INTO universidade.leciona VALUES (12,'P500');
INSERT INTO universidade.leciona VALUES (13,'P500');
INSERT INTO universidade.leciona VALUES (14,'P600');
INSERT INTO universidade.leciona VALUES (15,'P600');
INSERT INTO universidade.leciona VALUES (16,'P900');
INSERT INTO universidade.leciona VALUES (17,'P1300');
INSERT INTO universidade.leciona VALUES (18,'P1200');
INSERT INTO universidade.leciona VALUES (19,'P700');
INSERT INTO universidade.leciona VALUES (20,'P1500');
INSERT INTO universidade.leciona VALUES (21,'P1500');
INSERT INTO universidade.leciona VALUES (22,'P100');

INSERT INTO universidade.cursa VALUES('E112', 7,4.1);
INSERT INTO universidade.cursa VALUES('E102', 7,10);
INSERT INTO universidade.cursa VALUES('E104', 7,7);
INSERT INTO universidade.cursa VALUES('E109', 7,8);

INSERT INTO universidade.cursa VALUES('E112', 8,5.5);
INSERT INTO universidade.cursa VALUES('E102', 8,10);
INSERT INTO universidade.cursa VALUES('E107', 8,9);
INSERT INTO universidade.cursa VALUES('E108', 8,8.5);
INSERT INTO universidade.cursa VALUES('E109', 8,10);

INSERT INTO universidade.cursa VALUES('E104',5,8.7);
INSERT INTO universidade.cursa VALUES('E109',5,NULL);
INSERT INTO universidade.cursa VALUES('E110',20,5.5);
INSERT INTO universidade.cursa VALUES('E111',20,10.0);

INSERT INTO universidade.cursa VALUES('E101', 2,10.0);
INSERT INTO universidade.cursa VALUES('E107', 2,10.0);
INSERT INTO universidade.cursa VALUES('E106', 2,10.0);
INSERT INTO universidade.cursa VALUES('E104', 2,10.0);
INSERT INTO universidade.cursa VALUES('E105', 2,10.0);

INSERT INTO universidade.cursa VALUES('E101',22,NULL);
INSERT INTO universidade.cursa VALUES('E111',22,NULL);
INSERT INTO universidade.cursa VALUES('E106',22,9.5);
INSERT INTO universidade.cursa VALUES('E108',22,9.5);
INSERT INTO universidade.cursa VALUES('E109',22,9.5);
INSERT INTO universidade.cursa VALUES('E110',22,8.1);

INSERT INTO universidade.cursa VALUES('E112',6, NULL);
INSERT INTO universidade.cursa VALUES('E102',6,NULL);
INSERT INTO universidade.cursa VALUES('E104',6,NULL);
INSERT INTO universidade.cursa VALUES('E106',6,NULL);
INSERT INTO universidade.cursa VALUES('E107',6,NULL);
INSERT INTO universidade.cursa VALUES('E108',21,NULL);
INSERT INTO universidade.cursa VALUES('E109',21,NULL);
INSERT INTO universidade.cursa VALUES('E111',21,NULL);

INSERT INTO universidade.cursa VALUES('E106',9,NULL);
INSERT INTO universidade.cursa VALUES('E110',9,NULL);
INSERT INTO universidade.cursa VALUES('E111',9,NULL);
INSERT INTO universidade.cursa VALUES('E108',9,NULL);

INSERT INTO universidade.cursa VALUES('E108',11,NULL);
INSERT INTO universidade.cursa VALUES('E107',11,NULL);
INSERT INTO universidade.cursa VALUES('E110',11, NULL);


INSERT INTO universidade.cursa VALUES('E101',12,9.5);
INSERT INTO universidade.cursa VALUES('E111',12,7.6);
INSERT INTO universidade.cursa VALUES('E110',12,7.7);

INSERT INTO universidade.cursa VALUES('E106',3,9.0);
INSERT INTO universidade.cursa VALUES('E110',3,NULL);
INSERT INTO universidade.cursa VALUES('E101',3,7.0);
INSERT INTO universidade.cursa VALUES('E102',3,2.5);
INSERT INTO universidade.cursa VALUES('E107',3,3.2);

INSERT INTO universidade.cursa VALUES('E101',13,8.0);
INSERT INTO universidade.cursa VALUES('E111',13,8.0);
INSERT INTO universidade.cursa VALUES('E109',13,4.0);

INSERT INTO universidade.cursa VALUES('E101', 15,4.0);
INSERT INTO universidade.cursa VALUES('E111', 15,3.5);
INSERT INTO universidade.cursa VALUES('E107', 15,2.0);
INSERT INTO universidade.cursa VALUES('E102', 15,8.0);
INSERT INTO universidade.cursa VALUES('E112', 15,6.0);

INSERT INTO universidade.cursa VALUES('E106', 18,6.0);
INSERT INTO universidade.cursa VALUES('E111', 18,7.5);
INSERT INTO universidade.cursa VALUES('E109', 18,6.0);
INSERT INTO universidade.cursa VALUES('E110', 18,9.0);

INSERT INTO universidade.cursa VALUES('E102', 14,7.5);
INSERT INTO universidade.cursa VALUES('E104', 14,6.0);
INSERT INTO universidade.cursa VALUES('E106', 16,10.0);
INSERT INTO universidade.cursa VALUES('E107', 16,0.0);
INSERT INTO universidade.cursa VALUES('E108', 16,9.0);
INSERT INTO universidade.cursa VALUES('E110', 17, 8.5);

INSERT INTO universidade.cursa VALUES('E101',23,8.0);
INSERT INTO universidade.cursa VALUES('E105',23,8.0);
INSERT INTO universidade.cursa VALUES('E109',23,4.0);

INSERT INTO universidade.cursa VALUES('E101', 24,4.0);
INSERT INTO universidade.cursa VALUES('E110', 24,3.5);
INSERT INTO universidade.cursa VALUES('E107', 24,2.0);
INSERT INTO universidade.cursa VALUES('E102', 24,8.0);
INSERT INTO universidade.cursa VALUES('E111', 24,6.0);

INSERT INTO universidade.cursa VALUES('E106', 25,6.0);
INSERT INTO universidade.cursa VALUES('E111', 25,7.5);
INSERT INTO universidade.cursa VALUES('E109', 25,6.0);
INSERT INTO universidade.cursa VALUES('E112', 25,9.0);














