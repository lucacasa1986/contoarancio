drop table if exists categorie;
create table categorie (
  id integer primary key autoincrement,
  descrizione text not null,
  colore text not null
);

drop table if exists movimenti;
create table movimenti (
  id integer primary key autoincrement,
  tipo text not null,
  descrizione text not null,
  data_movimento text not null,
  importo real not null ,
  row_hash text not null,
  categoria_id integer,
  FOREIGN KEY(categoria_id) REFERENCES categorie(id)
);