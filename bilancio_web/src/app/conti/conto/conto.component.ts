import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router'; 

@Component({
  selector: 'app-conto',
  templateUrl: './conto.component.html',
  styleUrls: ['./conto.component.css']
})
export class ContoComponent implements OnInit {

  private idConto:number;

  constructor(private route: ActivatedRoute) {
    this.route.params.subscribe(res => {
      console.log(res.idConto);
      this.idConto = res.idConto;
    });
   }

  ngOnInit() {
  }

}
