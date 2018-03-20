create table categorie
(
	id integer
		primary key
		 autoincrement,
	descrizione text not null,
	colore text not null,
	icon_class TEXT
)
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
	id INTEGER
		primary key
		 autoincrement,
	titolare TEXT,
	descrizione TEXT
)
;

create table movimenti
(
	id INTEGER
		primary key
		 autoincrement,
	tipo TEXT not null,
	descrizione TEXT not null,
	data_movimento TEXT not null,
	importo REAL not null,
	row_hash TEXT not null,
	categoria_id INTEGER
		references categorie,
	conto_id INT
		constraint movimenti_conti_id_fk
			references conti
)
;

create table tags
(
	id INTEGER
		primary key
		 autoincrement,
	value TEXT not null,
	name TEXT not null
)
;

create table movimento_tags
(
	id INTEGER
		primary key
		 autoincrement,
	movimento_id INT not null
		constraint movimento_tags_movimenti_id_fk
			references movimenti,
	tag_id INT not null CONSTRAINT movimento_tags_tags_id_fk REFERENCES tags
)
;

