import { Routes } from '@angular/router';
import { LoginComponent } from './login/login';
import { ChatComponent } from './chat/chat';

export const routes: Routes = [
  { path: '', component: LoginComponent, pathMatch: 'full' },
  { path: 'chat', component: ChatComponent },
  { path: '**', redirectTo: '' }
];
