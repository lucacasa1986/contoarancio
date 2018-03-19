import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Movimento } from './movimento.model';

@Injectable()
export class MovimentoServiceService {

  constructor(private http:HttpClient) { }

  getMovements(dateFrom: Date, dateTo:Date, selectedCategories:Array<{}>) {
    let params = {
      from_date: this.formatDate(dateFrom),
      to_date:  this.formatDate(dateTo)
    }
    if ( selectedCategories )
    {
      params["category"] = selectedCategories.map(function(category:{}){
        return category["id"];
      });
    }
    return this.http.get("/api", {
      params: params
    });
  }

  getAllCategories() {
    return this.http.get("/api/categories");
  }

  updateCategory(category:Object) {
    return this.http.post("/api/categories", category);
  }

  updateMovimento(movimento:Movimento) {
    return this.http.put("/api/movimento", movimento);
  }

  uploadFile(file:File, type:string)
  {
    const endpoint = '/api/parse';
    const formData: FormData = new FormData();
    formData.append('excel_file', file, file.name);
    formData.append('type', type);
    return this.http
      .post(endpoint, formData);
  }

  formatDate(date:Date)
  {
    return date.getFullYear()+"-"+ (date.getMonth()+1) + "-" + date.getDate()
  }
}
