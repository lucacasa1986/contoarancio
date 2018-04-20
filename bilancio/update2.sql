ALTER TABLE movimenti ADD sottocategoria_id int NULL;
ALTER TABLE movimenti
ADD CONSTRAINT movimenti_sottocategorie_id_fk
FOREIGN KEY (sottocategoria_id) REFERENCES sottocategorie (id);

ALTER TABLE regole ADD subcategory_id int NULL;
ALTER TABLE regole
ADD CONSTRAINT regole_sottocategorie_id_fk
FOREIGN KEY (subcategory_id) REFERENCES sottocategorie (id);
