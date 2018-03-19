import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ListaContiComponent } from '../conti/lista-conti/lista-conti.component';
import { ContoComponent } from '../conti/conto/conto.component';

const routes: Routes = [
  {
      path: '',
      component: ListaContiComponent
  },
  {
    path: 'conto/:idConto',
    component: ContoComponent
  }
];

@NgModule({
  imports: [
    CommonModule, RouterModule.forRoot(routes)
  ],
  exports: [
    RouterModule
  ],
  declarations: []
})
export class AppRoutingModule { }
