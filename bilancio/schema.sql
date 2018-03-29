create table categorie
(
	id int auto_increment
		primary key,
	descrizione text not null,
	colore text not null,
	icon_class text null
)
engine=InnoDB
;

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

create table conti
(
	id int auto_increment
		primary key,
	titolare text null,
	descrizione text null
)
engine=InnoDB
;

CREATE TABLE `movimenti` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tipo` text NOT NULL,
  `descrizione` text NOT NULL,
  `data_movimento` date NOT NULL,
  `importo` double NOT NULL,
  `row_hash` text NOT NULL,
  `categoria_id` int(11) DEFAULT NULL,
  `conto_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `movimenti_conti_id_fk` (`conto_id`),
  KEY `movimenti_categorie_id_fk` (`categoria_id`),
  CONSTRAINT `movimenti_categorie_id_fk` FOREIGN KEY (`categoria_id`) REFERENCES `categorie` (`id`),
  CONSTRAINT `movimenti_conti_id_fk` FOREIGN KEY (`conto_id`) REFERENCES `conti` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=latin1;

CREATE TABLE `tags` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `value` text NOT NULL,
  `name` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;

CREATE TABLE `movimento_tags` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movimento_id` int(11) NOT NULL,
  `tag_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `movimento_tags_tags_id_fk` (`tag_id`),
  KEY `movimento_tags_movimenti_id_fk` (`movimento_id`),
  CONSTRAINT `movimento_tags_movimenti_id_fk` FOREIGN KEY (`movimento_id`) REFERENCES `movimenti` (`id`),
  CONSTRAINT `movimento_tags_tags_id_fk` FOREIGN KEY (`tag_id`) REFERENCES `tags` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=latin1;