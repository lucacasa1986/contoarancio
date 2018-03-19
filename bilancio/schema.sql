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

create table movimento_tags
(
	id INTEGER
		primary key
		 autoincrement,
	movimento_id INT not null
		constraint movimento_tags_movimenti_id_fk
			references movimenti,
	tag_id INT not null
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

alter table movimento_tags
	add constraint movimento_tags_tags_id_fk
		foreign key (tag_id) references tags
;

