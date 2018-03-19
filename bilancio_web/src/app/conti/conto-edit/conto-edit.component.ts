import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { MovimentoServiceService } from '../../movimenti/movimento-service.service';

@Component({
  selector: 'app-conto-edit',
  templateUrl: './conto-edit.component.html',
  styleUrls: ['./conto-edit.component.css']
})
export class ContoEditComponent implements OnInit {

  titolare:string = '';
  descrizione:string = '';

  @Output() contoAggiunto:EventEmitter<{}> = new EventEmitter<{}>();

  constructor(private _service:MovimentoServiceService) { }

  ngOnInit() {
  }

  onCreaConto() {
    this._service.creaNuovoConto(this.titolare, this.descrizione).subscribe(
      data => { this.contoAggiunto.emit({
        "id": data,
        "titolare": this.titolare,
        "descrizione": this.descrizione
      })}
    )
  }

  canCreate() {
    if ( this.titolare.length > 0 && this.descrizione.length > 0) {
      return true;
    }
    else {
      return false;
    }
  }

}
