import { Component } from '@angular/core';
import { TagService } from './tag.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'app';

  constructor( private _tagService: TagService)
  {
    _tagService.init();
  }
}
