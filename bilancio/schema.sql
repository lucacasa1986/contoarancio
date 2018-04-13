CREATE TABLE categorie
(
  id          INT AUTO_INCREMENT
    PRIMARY KEY,
  descrizione TEXT NOT NULL,
  colore      TEXT NOT NULL,
  icon_class  TEXT NULL
)
  ENGINE = InnoDB;
ALTER TABLE categorie ADD tipo TINYTEXT NULL;


INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (1, 'Trasporti', '#EC671A', 'fa fa-plane');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (2, 'Utenze', '#FF69B8', 'fa fa-bath');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (3, 'Assicurazioni e Finanziamenti', '#21A5BA', 'fa fa-umbrella');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (4, 'Bambini', '#5E35B2', 'fa fa-child');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (5, 'Animali domestici', '#558B2C', 'fa fa-paw');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (6, 'Casa', '#558B2F', 'fa fa-home');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (7, 'Scuola', '#3E2723', 'fa fa-book');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (8, 'Medicine e spese sanitarie', '#006B61', 'fa fa-medkit');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (9, 'Shopping', '#283593', 'fa fa-shopping-bag');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (10, 'Cura della persona', '#CC99FF', 'fa fa-user-circle');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (11, 'Tempo libero e viaggi', '#87BAE4', 'fa fa-glass');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (12, 'Cibo e spese', '#A6339D', 'fa fa-shopping-cart');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (13, 'Altre spese', '#616161', 'fa fa-money');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (14, 'Investimenti', '#9C9D43', 'fa fa-bar-chart');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (15, 'Patrimonio', '#F9A825', 'fa fa-diamond');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (16, 'Contabilita', '#558B4E', 'fa fa-dollar');
INSERT INTO categorie (id, descrizione, colore, icon_class) VALUES (17, 'Tasse e sanzioni', '#5E35B1', 'fa fa-legal');

update categorie set tipo='OUT';

INSERT INTO categorie (descrizione, colore, icon_class, tipo) VALUES ('Stipendio', '#558B4E', 'fa fa-dollar', 'IN');

CREATE TABLE conti
(
  id          INT AUTO_INCREMENT
    PRIMARY KEY,
  titolare    TEXT NULL,
  descrizione TEXT NULL
)
  ENGINE = InnoDB;

CREATE TABLE movimenti
(
  id             INT AUTO_INCREMENT
    PRIMARY KEY,
  tipo           TEXT   NOT NULL,
  descrizione    TEXT   NOT NULL,
  data_movimento DATE   NOT NULL,
  importo        DOUBLE NOT NULL,
  row_hash       TEXT   NOT NULL,
  categoria_id   INT    NULL,
  conto_id       INT    NULL,
  CONSTRAINT movimenti_categorie_id_fk
  FOREIGN KEY (categoria_id) REFERENCES categorie (id),
  CONSTRAINT movimenti_conti_id_fk
  FOREIGN KEY (conto_id) REFERENCES conti (id)
)
  ENGINE = InnoDB;

CREATE INDEX movimenti_categorie_id_fk
  ON movimenti (categoria_id);

CREATE INDEX movimenti_conti_id_fk
  ON movimenti (conto_id);

CREATE TABLE movimento_tags
(
  id           INT AUTO_INCREMENT
    PRIMARY KEY,
  movimento_id INT NOT NULL,
  tag_id       INT NOT NULL,
  CONSTRAINT movimento_tags_movimenti_id_fk
  FOREIGN KEY (movimento_id) REFERENCES movimenti (id)
)
  ENGINE = InnoDB;

CREATE INDEX movimento_tags_movimenti_id_fk
  ON movimento_tags (movimento_id);

CREATE INDEX movimento_tags_tags_id_fk
  ON movimento_tags (tag_id);

CREATE TABLE tags
(
  id    INT AUTO_INCREMENT
    PRIMARY KEY,
  value TEXT NOT NULL,
  name  TEXT NOT NULL
)
  ENGINE = InnoDB;

ALTER TABLE movimento_tags
  ADD CONSTRAINT movimento_tags_tags_id_fk
FOREIGN KEY (tag_id) REFERENCES tags (id);


CREATE TABLE regole
(
    id int PRIMARY KEY AUTO_INCREMENT,
    category_id int NOT NULL,
    name text NOT NULL,
    CONSTRAINT regole_categorie_id_fk FOREIGN KEY (category_id) REFERENCES categorie (id)
);

CREATE TABLE regole_condizione
(
    id int PRIMARY KEY AUTO_INCREMENT,
    field text NOT NULL,
    operator text NOT NULL,
    regola_id int NOT NULL,
    CONSTRAINT regole_condizione_regole_id_fk FOREIGN KEY (regola_id) REFERENCES regole (id)
);

ALTER TABLE regole_condizione ADD value text NULL;

ALTER TABLE regole ADD priority int NULL;
CREATE UNIQUE INDEX regole_priority_uindex ON regole (priority);