import { Component, OnInit } from '@angular/core';
import { MovimentoServiceService } from '../../movimenti/movimento-service.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-lista-conti',
  templateUrl: './lista-conti.component.html',
  styleUrls: ['./lista-conti.component.css']
})
export class ListaContiComponent implements OnInit {

  constructor(private _service:MovimentoServiceService, private router:Router) { }

  listaConti: Array<{}>;

  ngOnInit() {
    this._service.getConti().subscribe(
      data => this.listaConti = (data as Array<{}>)
    );
  }

  addConto(value:{})
  {
    this.listaConti.push(value);
    this.router.navigate(['/conto/'+value["id"]]);
  }

}
