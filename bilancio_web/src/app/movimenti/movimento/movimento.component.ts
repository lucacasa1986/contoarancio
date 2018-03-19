import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { Movimento } from '../movimento.model';
import { MovimentoServiceService } from '../movimento-service.service';
import { TagService } from '../../tag.service';

@Component({
  selector: 'app-movimento',
  templateUrl: './movimento.component.html',
  styleUrls: ['./movimento.component.css']
})
export class MovimentoComponent implements OnInit {

  @Input() movimento: Movimento;
  @Input() categorie: Object[];
  @Output() movimentoUpdate: EventEmitter<Movimento> = new EventEmitter<Movimento>();
  isVisible: Boolean = false;
  taggedSubcategories = [];
  subcategories: string[];

  constructor(private _service:MovimentoServiceService, private tagService:TagService) { }

  ngOnInit() {
    this.subcategories = this.tagService.allTags;
    this.tagService.getTagForMovimento(this.movimento["id"]).subscribe(
      data => {
        this.taggedSubcategories = (data as any[]).map(function(element){
          return element.name;
        });
      }
    )
  }

  onChangeSelectedCategory(value) {
    this.movimento["categoria_id"] = value;
    //update!
    this._service.updateMovimento(this.movimento).subscribe(
      data => { this.movimentoUpdate.emit(this.movimento);}
    )
  }

  cambiaCategoria(categoria:{})
  {
    this.movimento["categoria_id"] = categoria["id"];
    //update!
    this._service.updateMovimento(this.movimento).subscribe(
      data => { this.movimentoUpdate.emit(this.movimento);}
    )
  }

  getCategoria() {
    for(let categoria of this.categorie)
    {
      if (categoria['id'] == this.movimento['categoria_id'])
      {
        return categoria;
      }
    }
    return null;
  }

  getCategoriaColoreById()
  {
    let categoria = this.getCategoria();
    if ( categoria){
      return categoria['colore'];
    }
    return 'black';
  }

  getCategoriaIcon() {
    let categoria = this.getCategoria();
    if ( categoria){
      return categoria['icon_class'];
    }
    return 'fa fa-question';
  }

  getCategoriaDescription() {
    let categoria = this.getCategoria();
    if ( categoria){
      return categoria['descrizione'];
    }
    return '';
  }

  addTag(value:{}){
    this.tagService.addNewTag(this.movimento["id"], value["value"]).subscribe(
      data => {}
    )
  }

  removeTag(value:{})
  {
    let tag_value;
    if ('string' === typeof value) {
      tag_value = value;
    }
    else {
      tag_value = value["value"];
    }
    this.tagService.deleteTag(this.movimento["id"], tag_value).subscribe(
      data => {}
    )
  }

}
