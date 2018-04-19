create table sottocategorie
(
	id int auto_increment
		primary key,
	categoria_id int not null,
	descrizione text not null,
	constraint sottocategorie_categorie_id_fk
		foreign key (categoria_id) references categorie (id)
)
engine=InnoDB
;

create index sottocategorie_categorie_id_fk
	on sottocategorie (categoria_id)
;