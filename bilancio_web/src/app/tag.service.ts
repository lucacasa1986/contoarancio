import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

@Injectable()
export class TagService {

  allTags:string[] = [];

  constructor(private http:HttpClient) { }

  init() {
    this.http.get("/api/tags").subscribe(
      data => {
        this.allTags = (data as any[]).map(function(element){
          return element.name;
        });
      }
    );
  }

  getAllTags() {
    return this.allTags;
  }

  addNewTag(movimento_id: number, tag_value:string) {
    if ( this.allTags.indexOf(tag_value) < 0 ) {
      this.allTags.push(tag_value);
    }
    return this.http.put("/api/tag/"+movimento_id+"/" + tag_value,{});
  }

  deleteTag(movimento_id: number, tag_value:string) {
    return this.http.delete("/api/tag/"+movimento_id+"/" + tag_value);
  }

  getTagForMovimento(movimento_id: number) {
    return this.http.get("/api/tag/"+movimento_id);
  }

}
